### infra command

1. To start the entire infrastructure, run the following command:
```bash
docker compose -f infra/docker-compose.yml up -d
```

2. If you want to start specific services, you can specify them as follows:

```bash
docker compose -f infra/docker-compose.yml up kafka minio -d
```

3. To stop the infrastructure, run:
```bash
docker compose -f infra/docker-compose.yml down
```



### simulator command

1. To set up the Python environment for the sensor simulator, run the following command:
```bash
uv sync
```

2. source the environment:
```bash
source .venv/bin/activate
```

3. To start the sensor simulator, run the following command:
```bash
python services/sensor_simulator/sensor_simulator.py
```