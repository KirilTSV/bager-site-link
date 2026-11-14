# BAGER SITE LINK — logo release acceptance

The approved logo is the user's supplied BAGER SITE LINK illustration, not a newly generated or substitute mark.

## Confirmed defect
The `templates/app.html` header references `/static/bager-site-link-logo.jpg`, but the asset could not be retrieved from GitHub main; the supplied Android screenshot shows a broken image in the upper-left corner.

## Release acceptance
- Upload the exact approved image as `static/bager-site-link-logo.jpg` (binary file, not a placeholder).
- Verify HTTP 200 and `image/jpeg` on the deployed static URL.
- Check visible, uncropped branding in every participant role (dispatcher, excavator operator, truck driver, supervisor, client) on Android and iPhone.
- Confirm responsive sizing, cache refresh and no broken image on slow connection.
- Do not label logo rollout complete until these checks pass.
