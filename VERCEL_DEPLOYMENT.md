# Live Vercel deployment

Live application: https://online-traffic-violation.vercel.app

Dashboard: https://vercel.com/preksha-gohel/online-traffic-violation

This deployment uses the complete application from repository commit
`5f31f9ab27c2ecb4778d3ebee532e825b7cf49dd`, with the cloud configuration and
compatibility changes described below. The cloud configuration is committed to GitHub so automatic deployments
build the complete application. The original local project and the three member upload folders are
preserved separately.

## Hosting and durable data

The React frontend is compiled in `Dockerfile.vercel`. A Vercel container service
runs the existing Flask API and serves the compiled React application on the
same HTTPS origin. A separate Vercel daemon processes queued video jobs using
the existing CPU detection/tracking worker. Both use the same built image.

A new, separate Supabase project provides PostgreSQL and a private evidence
bucket. The existing local database and any earlier databases were not used or
changed. Only newly generated fictional accounts, vehicles and demonstration
cases were loaded into the new cloud database.

The Vercel project is `online-traffic-violation`, in the `preksha-gohel` team.
The new Marketplace database resource is `online-traffic-violation-db`, in
Mumbai. It uses the Supabase Free plan and Vercel Hobby plan; operation is
subject to their free quotas. The video worker is a continuously running
daemon and consumes those quotas while running, including idle time.

## Cloud compatibility changes

- Browser API requests can use the same origin, avoiding localhost addresses
  and cross-origin login failures on the deployed site.
- The web entrypoint serves React routes and keeps API authorization intact.
- PostgreSQL prepared statements are disabled for Supabase transaction pooling.
- Explicit `ENABLE_DEMO_FEATURES=1` allows authenticated RTO/Admin users to run
  the bundled demonstration video and dataset examples in the cloud. Citizen
  access remains denied, and the local bulk seeding CLI remains restricted.
- Models are downloaded and checksum-verified while building the image.
- Credentials, local data, account files and installed dependencies are excluded
  from source uploads and the container build context.

No real payment gateway or official registration connection is configured.
Payments are sandbox records and notifications are previews, as in the college
project. Camera experiments continue to require an RTO's review.

## Verification performed

- All 38 backend checks passed across the full suite and the dedicated real
  video/cloud checks. The real model test was rerun after provisioning its model.
- Three React tests passed, and the production React build succeeded.
- Vercel configuration was validated against its current official schema.
- The actual production container and worker image built and deployed on Vercel.
- Live HTTP checks passed for all five seeded accounts, private evidence,
  role access restrictions, government redaction and PDF receipts.
- A real bundled video was processed by the cloud worker. Its resulting case
  was reviewed by the RTO, assigned to a fictional demo owner, paid in the
  sandbox by that citizen, and exported as a PDF receipt.

The private account guide is supplied separately. Do not upload account files,
`.env` files, `.vercel/` or the runtime `data/` directory to GitHub.

## Further deployments

Link this directory to the existing Vercel project before deploying, using the
intended Vercel account. Preserve the existing production environment variables
and separate Supabase resource. Deploy from this source directory, not from
the original pre-cloud GitHub commit alone.

`deploy/bootstrap_cloud.py` was used once to initialize the new empty database.
It is a guarded administrative CLI, is not run by normal web/worker startup,
and refuses to initialize a populated or unexpected database. Do not rerun it
to reset a working deployment.

Normal redeployments use the same durable database and evidence bucket. They
do not reseed or clear existing records.
