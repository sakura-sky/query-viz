# Security Policy

`query-viz` renders untrusted data into an image. It does not touch the network,
the filesystem, or credentials, so its attack surface is small — but a renderer
that accepts arbitrary input can still be pushed into excessive resource use, so
we take those reports seriously.

## Reporting a vulnerability

**Please do not file public issues for security bugs.** Use one of:

- Email: `security@sakurasky.com`.
- GitHub Security Advisory: open a draft advisory at
  <https://github.com/sakura-sky/query-viz/security/advisories/new>.

Include a minimal repro: the rows and the `render_chart` arguments, the version
you reproduced against, and the impact you observed. We aim to acknowledge
within 3 business days.

## Scope

In scope:

- Input that causes unbounded memory or CPU use disproportionate to its size
  (a resource-exhaustion / DoS vector for a server calling `render_chart`).
- A crash that escapes as something other than `ChartError` / a normal
  exception the caller can catch (e.g. a segfault in the rendering backend).

Out of scope:

- Bugs in `matplotlib` itself — report those upstream. We mitigate downstream
  where we can.
- "The chart looks wrong." Rendering-quality issues are normal bugs; file a
  regular issue.

## Notes for callers

`query-viz` does not bound the number of rows or series you hand it — that's the
caller's job. If you render user-driven queries, cap the row count *before*
calling `render_chart` (the marketing agent it was extracted from does this via
a max-rows guard). `render_chart` also coerces non-numeric `y` values to `0.0`
rather than raising, so malformed data degrades to a chart rather than an error.
