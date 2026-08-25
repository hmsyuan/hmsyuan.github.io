# PTT2 to Hugo exporter

This directory contains a read-only importer for public PTT2 boards. The first
target board is `InAddition`.

The initial probe verifies three things before the full importer is enabled:

1. a GitHub-hosted runner can reach PTT2 over WebSocket;
2. guest access can read the public board and its article list;
3. the board's `z` (essence/man) root screen can be parsed reliably.

Credentials are optional. The probe uses `guest` by default. If PTT2 requires
a registered account, set `PTT2_ID` and `PTT2_PASSWORD` as repository secrets;
never commit credentials.

The completed exporter will produce a ZIP rooted at `content/posts/ptt2/` plus
an import manifest, so it can be copied into this Hugo repository or reviewed
through a draft pull request before publication.

