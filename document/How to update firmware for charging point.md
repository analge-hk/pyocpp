# How to update firmware for charging point

#### Step 1 Upload frimware to websrv

```ssh
winscp upload zwzx-v1.12.20.mzip file to /var/www/html/download/
```



#### Step 2 Upgrade firmware

```sh
# ssh login in Pi and Start python program
python3 -u pycmd.py

# Enter the firmware upgrade command, such as the upgrade of CP2
2 upate http://65.52.164.18:8000/download/zwzx-v1.12.20.mzip
```

