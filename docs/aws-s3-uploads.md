# Private S3 uploads

Use a private bucket in `af-south-1` (or the configured region), with Block Public
Access enabled and Object Ownership set to **Bucket owner enforced**. Do not use
object ACLs or public URLs. Enable default SSE-S3 encryption (or approved KMS), and
consider versioning according to retention policy.

Configure exact staging/production web origins in the bucket CORS policy; allow only
`PUT`, `GET`, and `HEAD`, `Content-Type`, and expose `ETag`. Never use `*` for
production origins. Add a lifecycle rule to abort incomplete multipart uploads after
seven days. A future cleanup job should expire pending database upload intents and
delete their objects where present.

The application role needs only `s3:PutObject`, `s3:GetObject` (also authorizes
HeadObject), and `s3:DeleteObject` on `arn:aws:s3:::<BUCKET>/gyms/*`. Do not grant
bucket-policy, ACL, lifecycle, or broad `s3:*` permissions. Attach this policy to the
EC2/ECS role; local development may use the standard AWS credential chain or LocalStack
via `AWS_S3_ENDPOINT_URL`.

Required settings: `AWS_REGION`, `AWS_S3_UPLOADS_BUCKET`, and bounded presign expiry
values. Credentials are intentionally optional so workload IAM roles work normally.

Verify infrastructure without changing it:

```bash
aws sts get-caller-identity
aws s3api get-public-access-block --bucket "$AWS_S3_UPLOADS_BUCKET"
aws s3api get-bucket-encryption --bucket "$AWS_S3_UPLOADS_BUCKET"
aws s3api get-bucket-ownership-controls --bucket "$AWS_S3_UPLOADS_BUCKET"
aws s3api get-bucket-cors --bucket "$AWS_S3_UPLOADS_BUCKET"
aws s3api get-bucket-lifecycle-configuration --bucket "$AWS_S3_UPLOADS_BUCKET"
```

Deploy by applying the migration, setting the bucket/role configuration, and verifying
presigned upload, completion, download, replacement, and cleanup with harmless test
files. Database downgrade does not delete S3 objects; remove test objects separately.
