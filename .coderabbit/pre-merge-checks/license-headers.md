---
id: license-headers
name: License headers present
mode: warning
report: platform
paths:
  - "site/cds_rdm/**/*.py"
  - "site/tests/**/*.py"
  - "assets/**/*.js"
  - "site/cds_rdm/assets/**/*.js"
---

Pass when every **newly added** file in scope starts with the project license
header: a copyright line naming CERN with the current year, and a reference to
the GPL-2.0 license and the LICENSE file. Python uses the `# -*- coding: utf-8 -*-`
comment block, and JS uses a `//` comment block.

Fail and list the new files whose header is missing. Don't fail on modified
files whose copyright year wasn't extended; mention them as a note instead.
