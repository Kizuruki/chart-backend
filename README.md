# uc-chart-backend
Backend for UntitledCharts Sonolus server

# R2
This backend must be configured with a R2 instance from Cloudflare, or a S3 instance.

If it's just the server, use the static option in the sonoserver instead.

### Using S3
This backend was designed with **Cloudflare R2** in mind, and therefore will not work with S3 without modifications:
- Change the `location=` for your AWS location.