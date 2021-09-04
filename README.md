# ksci
Run arbitrary code in a remote Kubernetes cluster, stream logs and download artefacts. It works, but its usefulness is questionable. This project is mostly a playground for new infrastructure, system design and data processing ideas.

https://user-images.githubusercontent.com/1041380/122805877-5242b280-d2d2-11eb-81ba-ae280becbd3a.mp4


## TODO
Some feature ideas to implement in the future.
### Core logic
- [ ] Push logs and status changes to Kafka 
- [ ] New web socket service to notify clients of new logs and status changes
- [ ] Separate service to save log data to Cassandra (Go) via the API
- [ ] Separate service to check how much time each job is executing (status)
- [ ] Authentication with Algorand (send token to auth, get a session)

### UI
- [ ] Users
- [ ] Projects page
- [ ] Subscribe to projects and list projects the user subscribed to
- [ ] Last builds (all, subscribed) like Twitter 

#### Metrics
- [ ] Runs, log lines/bytes, run duration, run status (funnel)
- [ ] Kafka Streams/Flink for analytics
- [ ] Dashboard

### Development and deployment
- [ ] Integration tests with third party services in Kubernetes
- [ ] Docker build and push in Github Actions
- [ ] Deploy to Kubernetes from Github Actions/flux/argo
