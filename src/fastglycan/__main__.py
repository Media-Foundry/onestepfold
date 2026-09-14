"""Allow ``python -m fastglycan`` to invoke the CLI."""

from .cli import main

raise SystemExit(main())

