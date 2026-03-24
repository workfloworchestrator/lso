---
icon: lucide/clipboard-clock
---

# Task Executors

Tasks that are sent to LSO are run by an executor. The executor is responsible for running the Ansible playbook or
script that is requested by the API. The REST API that handles requests runs in a separate thread.

## Thread Pool

By default, LSO will use a thread pool executor to run tasks. This is the quickest way to get LSO up and running, as no
external services are required to do this. In the environment that LSO runs in (either locally, or in a container)
please configure `EXECUTOR` and `MAX_THREAD_POOL_WORKERS`. These both have default values, but can be overridden by the
user.

## Celery

One downside of the thread pool executor is the lack of scalability. Once the amount of thread pool workers is
exhausted, LSO will run into availability issues. One solution to this, is to run multiple worker nodes that subscribe
to a task queue. LSO uses [Celery](https://docs.celeryq.dev) to achieve this. This enables distributed execution for
running multiple tasks simultaneously. Configuring Celery is done by setting up a
[Redis](https://redis.io/docs/latest/) server, and setting the following environment variables.

```yaml
EXECUTOR: celery
CELERY_BROKER_URL: redis://localhost:6379/0
CELERY_RESULT_BACKEND: redis://localhost:6379/0
WORKER_QUEUE_NAME: lso-worker-queue  # Optional, default is None
```

Then, to start a Celery worker:
```sh
celery -A lso.worker worker --loglevel=info -Q $WORKER_QUEUE_NAME
```
