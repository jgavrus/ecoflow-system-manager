# EcoFlow metric manager

![img3.png](readme_pics/img3.png)

## WARNING!!

The project is under development. Can be some issues or bugs.  
Project based on [EcoFlow to Prometheus exporter](https://github.com/berezhinskiy/ecoflow_exporter/tree/master) by
Yaroslav Berezhinskiy.  
The project, for now, supports only one device at a time.

The system been tested only on Delta pro 3. Many old devices can be unsupported.  
In theory, devices from
[official documentation](https://developer-eu.ecoflow.com/us/document/generalInfo) fully supported.
Others need to test it.  
Expected that the user is already familiar with Prometheus and Grafana,
Python and Docker and understands what API is, etc.
EcoFlow sends different names of metrics for different device models.
So you may need to tune dashboards for your own model.

## Requirements

1. Python 3.11+
2. Already registered EcoFlow dev account
3. docker-compose
4. Knowledge of NGINX (optional)

## Installation guide

1. Setup all required credentials in [.env](.env) file
2. Run `docker-compose up -d`
3. Run `docker-compose logs -f` to see logs
4. After you see that all containers are up, go to Grafana and import dashboards  
   You can load dashboards in two ways:

- Import from Grafana by id ![img.png](readme_pics/img.png)
  ![img.png](readme_pics/img1.png)
- Import from [dashboard.json](dashboard.json)
  ![img2.png](readme_pics/img2.png)
- After loading dashboards, you can see metrics in Grafana.

## If you don't see any metrics in Grafana after importing dashboards

You can see logs in `docker-compose logs -f` and see what metrics your device receives from EcoFlow API.
![img.png](readme_pics/img4.png)
In the example you can see what metrics register exporter from EcoFlow API.  
`<apiMetricName> -> <prometheus\grafana_metric_name>`  
after this you can tune your dashboards to see metrics in Grafana.
![img.png](readme_pics/img5.png)  
Some metrics can be registered multiple times by different names.   
It is because Exporter uses two APIs at the same time.  
Official API and internal android app API with additional metrics.  
They are delivered many different metrics, andrid api has more detail metrics for some devices but at the same time ot
much instable.
The system has reconnection to both APIs in 30 seconds after detecting that one of them is down.  
Reconnect is a widespread case for android api, because it can be closed if you use mobile (android/ios) to see or
change some settings on your device.

## Alerting

The system has an alertmanager that uses Prometheus API to send alerts in Telegram.  
You can tune conditions to yourself needs [ecoflow.yml](prometheus/alerts/ecoflow.yml) file.

## NGINX proxy manager
This container is optional. Added for people who want to use https with a domain name.  
If you don't need it, you can remove it from docker-compose.yml.

## In Development:

I want to migrate from alermanager to custom api, that will trigger different actions in different situations.  
For example, change charging power based on daytime, integration with smart things like wall sockets, etc.  
It will be added to this project in the future when it will be ready.

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file.