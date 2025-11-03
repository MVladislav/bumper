# Bumper Origins & Maintenance

The **Bumper** project was originally created by [@torbjornaxelsson](https://github.com/torbjornaxelsson) in 2017 as a reverse engineering tool to interface with certain EcoVacs robotic vacuums.  
It successfully reached its initial goal and remained in a stable (but no longer actively maintained) state, with the last update committed in December 2017.

In early 2019, [@bmartin5692](https://github.com/bmartin5692) picked up the project to support newer vacuum models that use updated protocols. His fork introduced key changes and improvements to the original codebase and continued development for several years.

Later, [@edenhaus](https://github.com/edenhaus) forked the project to refactor and modernize large portions of the codebase, aiming to clean up architectural issues, enhance maintainability, and support more recent devices.  
This fork has since diverged significantly and is now actively maintained as the primary development source going forward.

## 🔧 Current Maintenance

This repository is now the **actively maintained** version of Bumper. It includes:

- Major refactors for stability and code clarity
- Updated support for newer EcoVacs models and protocols
- Improved documentation
- Better compatibility with modern environments

## 📦 Legacy Versions

If you're looking for the older versions:

- The original 2017 codebase by @torbjornaxelsson is archived.
- The intermediate development fork by @bmartin5692 is still available.
- A historical snapshot of the pre-refactor code is preserved as [`v0.1.0`](https://github.com/bmartin5692/bumper/tree/v0.1.0) in his fork.

> ⚠️ That legacy version may still work with some early models (e.g. M81 Pro, N79S),  
> but for all current and future use, this repository is recommended.
