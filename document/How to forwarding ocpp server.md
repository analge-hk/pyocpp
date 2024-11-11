# How to forwarding ocpp server



### On Raspberry Pi

```sh
# stop pyocpp and open ip forwarding
sudo sytemctl stop pyocpp
sudo sysctl -w net.ipv4.ip_forward=1
sudo iptables -t nat -I PREROUTING -p tcp --dport 9000 -j DNAT --to 137.116.167.87:6005
sudo iptables -t nat -I POSTROUTING -p tcp --dport 6005 -j MASQUERADE
sudo iptables -t nat --list

# close ip forwarding and start pyocpp
sudo iptables -t nat -D PREROUTING 1
sudo iptables -t nat -D POSTROUTING 1
sudo iptables -t nat --list
sudo systemctl start pyocpp

```


