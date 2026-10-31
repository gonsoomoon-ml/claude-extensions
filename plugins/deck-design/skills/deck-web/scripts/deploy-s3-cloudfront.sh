#!/usr/bin/env bash
# Publish a web deck folder as a public page: private S3 bucket (public access blocked) + CloudFront with Origin Access Control.
#
# usage: bash deploy-s3-cloudfront.sh <site-name> [web-dir] [region]
#   site-name  bucket = <site-name>-<account id>; the OAC and the CloudFront comment carry the same name
#   web-dir    folder with index.html, cover.png and figures (default: web)
#   region     bucket region (default: us-west-2)
#
# First run  = create bucket + OAC + distribution, upload, invalidate (creates a public surface — run it yourself, on purpose).
# Later runs = upload + invalidate only. Prints the https URL; CloudFront takes 3–5 minutes to serve the new files.
# Uploads index.html (text/html; charset=utf-8, max-age=300) and every image next to it; skips scripts, JSON, markdown, dotfiles.
# If cover.png exists, the og:image meta in index.html is rewritten to its absolute URL first (the preview card needs it absolute).
set -euo pipefail
NAME=${1:?site-name}; DIR=${2:-web}; REGION=${3:-us-west-2}
[ -f "$DIR/index.html" ] || { echo "no $DIR/index.html" >&2; exit 1; }
ACC=$(aws sts get-caller-identity --query Account --output text)
B="$NAME-$ACC"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT

if ! aws s3api head-bucket --bucket "$B" 2>/dev/null; then
  echo "creating bucket $B ($REGION)"
  if [ "$REGION" = "us-east-1" ]; then aws s3api create-bucket --bucket "$B" --region "$REGION" --output text --query Location
  else aws s3api create-bucket --bucket "$B" --region "$REGION" --create-bucket-configuration LocationConstraint="$REGION" --output text --query Location; fi
  aws s3api put-public-access-block --bucket "$B" --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
fi

ORIGIN="$B.s3.$REGION.amazonaws.com"
DIST=$(aws cloudfront list-distributions --query "DistributionList.Items[?Origins.Items[0].DomainName=='$ORIGIN'].Id | [0]" --output text 2>/dev/null || true)
if [ -z "$DIST" ] || [ "$DIST" = "None" ]; then
  OAC=$(aws cloudfront list-origin-access-controls --query "OriginAccessControlList.Items[?Name=='$NAME'].Id | [0]" --output text 2>/dev/null || true)
  if [ -z "$OAC" ] || [ "$OAC" = "None" ]; then
    echo "creating origin access control $NAME"
    OAC=$(aws cloudfront create-origin-access-control --origin-access-control-config \
      "Name=$NAME,SigningProtocol=sigv4,SigningBehavior=always,OriginAccessControlOriginType=s3" \
      --query OriginAccessControl.Id --output text)
  fi
  echo "creating distribution for $ORIGIN"
  cat > "$TMP/cf.json" <<JSON
{"CallerReference":"$NAME-$(date +%s)","Comment":"$NAME - web deck","DefaultRootObject":"index.html","Enabled":true,
 "PriceClass":"PriceClass_All","HttpVersion":"http2","IsIPV6Enabled":true,
 "Origins":{"Quantity":1,"Items":[{"Id":"S3-$B","DomainName":"$ORIGIN","OriginAccessControlId":"$OAC","S3OriginConfig":{"OriginAccessIdentity":""}}]},
 "DefaultCacheBehavior":{"TargetOriginId":"S3-$B","ViewerProtocolPolicy":"redirect-to-https",
   "CachePolicyId":"658327ea-f89d-4fab-a63d-7e88639e58f6","Compress":true,
   "AllowedMethods":{"Quantity":2,"Items":["GET","HEAD"],"CachedMethods":{"Quantity":2,"Items":["GET","HEAD"]}}},
 "ViewerCertificate":{"CloudFrontDefaultCertificate":true}}
JSON
  DIST=$(aws cloudfront create-distribution --distribution-config "file://$TMP/cf.json" --query Distribution.Id --output text)
  cat > "$TMP/policy.json" <<JSON
{"Version":"2012-10-17","Statement":[{"Sid":"AllowCloudFrontOACReadOnly","Effect":"Allow","Principal":{"Service":"cloudfront.amazonaws.com"},
 "Action":"s3:GetObject","Resource":"arn:aws:s3:::$B/*",
 "Condition":{"StringEquals":{"AWS:SourceArn":"arn:aws:cloudfront::$ACC:distribution/$DIST"}}}]}
JSON
  aws s3api put-bucket-policy --bucket "$B" --policy "file://$TMP/policy.json"
fi

DOM=$(aws cloudfront get-distribution --id "$DIST" --query Distribution.DomainName --output text)
if [ -f "$DIR/cover.png" ]; then
  sed -i "s|<meta property=\"og:image\" content=\"[^\"]*\">|<meta property=\"og:image\" content=\"https://$DOM/cover.png\">|" "$DIR/index.html"
fi
aws s3 cp "$DIR/index.html" "s3://$B/index.html" --content-type "text/html; charset=utf-8" --cache-control "max-age=300" --only-show-errors
aws s3 sync "$DIR" "s3://$B/" --exclude "*" --include "*.png" --include "*.jpg" --include "*.jpeg" --include "*.svg" --include "*.webp" \
  --exclude ".*" --only-show-errors
aws cloudfront create-invalidation --distribution-id "$DIST" --paths "/*" --query Invalidation.Id --output text
echo "URL  https://$DOM/   (3-5 min to propagate)"
