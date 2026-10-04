# Third-party licenses

Original companion SVG, derivative icons, source and project documentation are MIT licensed under this project's LICENSE. No OpenAI pet artwork, logo, usage-widget configuration or private integration code was copied.

Primary dependencies use their upstream licenses; this list is a pointer, not a replacement for a full locked transitive license review before release.

| Dependency                                      | Role                                                        | Upstream license                                     |
| ----------------------------------------------- | ----------------------------------------------------------- | ---------------------------------------------------- |
| Tauri and official plugins                      | Desktop runtime, tray, opening, shortcuts, startup, updates | MIT / Apache-2.0                                     |
| TypeScript                                      | Type checking                                               | Apache-2.0                                           |
| Vite, Vitest, Prettier                          | Build/test/format tooling                                   | MIT                                                  |
| Playwright                                      | UI tests                                                    | Apache-2.0                                           |
| axe-core / axe Playwright adapter               | Accessibility checks                                        | MPL-2.0; retain upstream package license files       |
| serde, serde_json, url, Tokio, tempfile, semver | Native local state and networking support                   | Upstream MIT / Apache-2.0 combinations; Tokio is MIT |
| reqwest                                         | HTTPS feed fetching                                         | MIT / Apache-2.0                                     |
| SHA-2, base64                                   | Update integrity encoding                                   | MIT / Apache-2.0                                     |
| minisign-verify, minisign                       | Signature verification / test signing                       | MIT                                                  |
| Gitleaks                                        | Local/CI secret detection tool                              | MIT                                                  |
| png                                             | Bounded local image decoding and metadata-free encoding     | MIT / Apache-2.0                                     |

Use `package-lock.json` and `src-tauri/Cargo.lock` as the exact inventory. Inspect npm package LICENSE files and Cargo registry crate license declarations, including transitive dependencies, during release review. Tool-only packages are not all shipped in the desktop executable. Do not add fonts/assets without corresponding license evidence.
