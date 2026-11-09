# Kenney Mini Characters 2.0

Original GLBs, shared palette PNG and licence from [Kenney](https://kenney.nl/assets/mini-characters), downloaded 2026-11-08. CC0-1.0; see License.txt. Sources, sizes and SHA-256 hashes are recorded in sources.json. The official download-link endpoint issues a short-lived archive URL.

Only the thirteen everyday human characters are bundled. No remote requests happen at runtime. Original geometry, normals, face, hair and palette remain intact. The office identity registry selects an original asset rather than recolouring it.

Run `.venv/bin/python scripts/build_kenney_characters.py` from the repository root to regenerate `web/lib/kenney-mini-data.mjs`. The deterministic standard-library converter separates rigidly weighted meshes by the original joints and bakes palette samples to linear vertex colours at runtime. It keeps the original idle and sit rotations. Source root motion is discarded because the app owns positioning; existing X-axis arm gestures and leg swing remain live. This avoids an asynchronous loader contract in the shared office/home builder.

World styling follows the official [Mini series](https://kenney.nl/assets/series:Mini), especially Mini Market and Mini Arcade: broad bevels, compact proportions, flat colours, simple tiled ground and distinct colour groups. These are observations from the reference images, not a published Kenney design specification. Reference images and local screenshots stay in ignored data/runtime/character-cute/design/.
