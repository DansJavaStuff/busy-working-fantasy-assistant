# Yahoo Fantasy API Compliance

This project is a personal-use fantasy football assistant built around the Yahoo Fantasy Sports API.

The application is designed to comply with Yahoo's published developer requirements and the terms applicable to this application's approved use.

## Scope

- Personal-use application only.
- Used only with the owner's own Yahoo Fantasy leagues and teams.
- Not operated as a commercial service.
- Not intended for public redistribution of Yahoo Fantasy data.

## API Access

- Yahoo Fantasy API access is treated as read-only.
- The application does not attempt to make roster, waiver, trade, lineup, or other league changes through the Yahoo API.
- Recommended actions are shown to the user, who performs them manually in Yahoo Fantasy.

## Yahoo Data Handling

Yahoo Fantasy data is treated as transient application data.

The application architecture is designed so that:

- API responses are used in memory for the current application session.
- Yahoo API data is not persisted into the application's SQLite database.
- Yahoo API data is not used to build a permanent indexed dataset.
- Local storage is reserved for application-owned settings, preferences, draft history, and other non-Yahoo application state.
- OAuth credentials and tokens are excluded from source control.

Manual HTML imports remain available as a fallback during development and are excluded from Git.

## Attribution

Pages that display Yahoo Fantasy information include clear Yahoo Fantasy attribution and link back to an official Yahoo Fantasy page.

The shared application footer is used so attribution remains consistent across relevant pages.

## Rate Limits and Reliability

The Yahoo provider is designed to avoid unnecessary API traffic.

The application should:

- reuse data within a request/session where appropriate,
- avoid repeated API calls on simple page rendering,
- handle API errors cleanly,
- handle authentication refresh safely,
- implement appropriate retry/backoff behaviour where required,
- fall back gracefully when Yahoo data is temporarily unavailable.

## Privacy and Distribution

Yahoo Fantasy information retrieved for this application is intended only for the owner's personal use.

The application does not provide a public Yahoo Fantasy data feed, API, or dataset.

## Security

The following must never be committed to Git:

- Yahoo Client Secret
- OAuth access tokens
- OAuth refresh tokens
- authorization responses containing credentials
- raw Yahoo source data containing sensitive/session information

Relevant files are excluded through `.gitignore`.

## Provider Architecture

Yahoo data access is isolated behind a provider layer.

This allows the application to use:

1. Yahoo Fantasy API data when available.
2. Manual Yahoo imports as a fallback during development or API outages.

The rest of the application should consume normalized provider data rather than depend directly on Yahoo response formats.

## Compliance Review

If Yahoo changes its API documentation, attribution requirements, rate limits, or developer terms, this application's Yahoo integration should be reviewed before relying on the changed behaviour.

The signed Yahoo agreement itself is confidential and is not stored in this public repository.
