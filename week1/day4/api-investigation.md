# API Investigation — Day 4

## Pagination
The API uses limit and skip query parameters to paginate results.
![SS1](images/Pagination-2.png)
![SS2](images/Pagination-1.png)

## Headers Observed
- User-Agent
- Authorization
- Content-Type
- Cache-Control
- ETag

![SS2](images/Headers.png)

## Header Manipulation Results
Removing User-Agent did/did not affect response.
Fake Authorization header was ignored by the public API.
![SS2](images/cmd.png)
![SS2](images/header_manipulation.png)


## Caching Behavior

ETag was returned by the server.
When re-sent using If-None-Match, server returned 304 Not Modified.
![SS2](images/caching.png)


## Request–Response Cycle
Client sends request with headers → server responds with status, headers, and body.
Caching headers allow clients to avoid downloading unchanged data.
![SS2](images/cycle.png)
