# SSH Synchronization Utility

## Prerequisites
- Python
- ```pip install -r requirements.txt```

## Synchronization
```bash
python ./sshsync.py ./sshsync.yaml ../src
```

## sshsync.yaml
```yaml
username:
password:
filter: (.+)
mapping: /remote/path/$1
url: ssh://hostname
```
