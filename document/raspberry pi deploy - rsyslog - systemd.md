# Deploy

## The `systemd` Daemon

https://www.cnblogs.com/xzlive/p/15180969.html

```
cp pyocpp.service
cp frpc.service

[/usr]/lib/systemd/system
or
/etc/systemd/system/pyocpp.service
or
/lib/systemd/system/pyocpp.service

view log
journalctl -u pyocpp.service -f
or
journalctl -u pyocpp.service --since="2021-04-28 09:17:16" -n18
or
tail -f /var/log/syslog
```



#### 树莓派 Raspberry PI 4B 上部署腾讯日志服务

树莓派不能安装64位 LogListener，通过rsyslog 送到 腾讯云服务器，再转到CLS

https://www.jianshu.com/p/34c101c17236

```shell
#安装rsyslog
sudo apt install rsyslog

#客户端配置
sudo nano /etc/rsyslog.conf 

# /etc/rsyslog.conf configuration file for rsyslog
#
# For more information install rsyslog-doc and see
# /usr/share/doc/rsyslog-doc/html/configuration/index.html


#################
#### MODULES ####
#################

module(load="imuxsock") # provides support for local system logging
module(load="imklog")   # provides kernel logging support
#module(load="immark")  # provides --MARK-- message capability

# provides UDP syslog reception
#module(load="imudp")
#input(type="imudp" port="514")

# provides TCP syslog reception
module(load="imtcp")
input(type="imtcp" port="514")

$PreserveFQDN on                                      # 允许主机名保留FQDN

# 配置使用TCP发送消息
*.* @@159.75.27.109:514

###########################
#### GLOBAL DIRECTIVES ####
###########################

#
# Use traditional timestamp format.
# To enable high precision timestamps, comment out the following line.
#
$ActionFileDefaultTemplate RSYSLOG_TraditionalFileFormat

#
# Set the default permissions for all log files.
#
$FileOwner root
$FileGroup adm
$FileCreateMode 0640
$DirCreateMode 0755
$Umask 0022

#
# Where to place spool and state files
#
$WorkDirectory /var/spool/rsyslog

#重启服务
sudo service rsyslog restart 

#客户端通过rsyslog传日志到了服务器端查看
tail -100f /var/log/syslog

# 在腾讯云配采集规则
/var/log/syslog
```

