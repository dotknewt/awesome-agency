# Understanding connection pooling in our API gateway

## Background

Our API gateway sits in front of roughly forty backend services, and until last quarter it opened a brand new TCP connection to each backend for every incoming request, which worked fine when traffic was low but started causing latency spikes and eventually connection refusals once we crossed about two thousand requests per second during peak hours, because the backend services themselves have connection limits configured at the operating system level that we hadn't accounted for when we originally built the gateway.

## What connection pooling does

Connection pooling solves this by keeping a set of already-established connections to each backend open and reusing them across requests instead of tearing a connection down and building a new one every single time, which sounds simple but actually requires careful tuning of pool size, idle timeout, and eviction policy, because a pool that is too small will queue requests waiting for a free connection while a pool that is too large will exhaust the backend's own connection limits and cause the exact latency spikes we were trying to avoid in the first place.

## How we sized our pools

We sized each backend's pool by looking at its p99 request duration and its typical concurrent request volume during peak traffic, then set the pool size to roughly twice the product of those two numbers divided by our target latency budget, which is a rough heuristic borrowed from Little's Law rather than an exact science, and we revisit the numbers quarterly as traffic patterns shift, especially after a backend team ships a change that meaningfully alters their own response times or the shape of their traffic.

## Rollout

We rolled this out gradually, one backend at a time, watching error rates and p99 latency in our dashboards before moving to the next one.

## Gotchas we hit

- Idle connections can go stale if a backend restarts without the pool noticing, so health checks matter.
- Pool metrics need their own dashboard; they get lost easily among general request metrics.
