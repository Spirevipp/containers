# Updates

Renovate groups minor/patch and image-digest updates per container and auto-merges
after checks pass. Major versions and Alpine release changes require manual
merging. Prereleases are ignored; releases normally wait three days.

## GitHub setup

1. Push the workflows and run **Container checks** once to register **Container CI**.
2. Create a private GitHub App under **Settings > Developer settings > GitHub Apps**.
   Use the repository URL as its homepage, disable webhooks, and install it only
   on this repository. Generate a private key and note the Client ID or numeric App ID.

   | Repository permission | Access |
   | --- | --- |
   | Contents, Pull requests, Workflows, Checks, Commit statuses, Issues | Read/write |
   | Administration, Dependabot alerts | Read-only |
   | Metadata | Automatic read-only |

3. Under repository **Settings > Secrets and variables > Actions**, add:

   | Kind | Name | Value |
   | --- | --- | --- |
   | Variable | `UPDATE_APP_ID` | App Client ID or numeric App ID |
   | Secret | `UPDATE_APP_PRIVATE_KEY` | Complete PEM contents |
   | Variable | `UPDATES_ENABLED` | Leave unset until setup is complete |
   | Variable | `REBUILDS_ENABLED` | Optional; leave unset to disable scheduled rebuilds |

4. Enable **Allow auto-merge** and **Allow squash merging** in repository settings.
   Protect `main`: require PRs, **Container CI** from GitHub Actions, and up-to-date
   branches. Block force pushes/deletion and give the App no bypass. Keep required
   approvals at zero for unattended minor updates.
5. Run **Check upstream updates** with `dry_run` checked. After it succeeds, set
   `UPDATES_ENABLED=true`. Optionally set `REBUILDS_ENABLED=true` too.

## Schedule

| Workflow | Schedule (UTC) | Enable variable |
| --- | --- | --- |
| Check upstream updates | 1st of each month, 02:17 | `UPDATES_ENABLED=true` |
| Rebuild all containers | 15th of each month, 04:23 | `REBUILDS_ENABLED=true` |

Both workflows can run manually. Set an enable variable to `false` to stop its
scheduled runs. Updates publish `:latest` after merging; versioned images still
use `<container>-v<version>` Git tags.
