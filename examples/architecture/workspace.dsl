workspace "Sensor Node" "Measures temperature and humidity and publishes the readings to a cloud platform." {

    model {
        installer = person "Installer" "Installs and commissions sensor nodes."
        analyst = person "Analyst" "Looks at the readings."
        mobileApp = softwareSystem "Commissioning App" "Configures a node over Bluetooth." "External"
        cloud = softwareSystem "Cloud Platform" "Collects readings from all nodes." "External"

        node = softwareSystem "Sensor Node" "Measures temperature and humidity and publishes the readings." {
            driver = container "Sensor Driver" "Reads the sensors on a timer." "C, FreeRTOS"
            buffer = container "Data Buffer" "Keeps readings while the network is down." "Ring buffer in flash"
            uplink = container "Uplink Client" "Publishes readings." "C, MQTT over TLS" {
                session = component "Session Manager" "Keeps the TLS session alive." "C"
                publisher = component "Publisher" "Builds and sends MQTT messages." "C"
            }
            updater = container "Firmware Updater" "Downloads and installs new firmware." "C, MCUboot"
        }

        installer -> mobileApp "Commissions nodes with"
        analyst -> cloud "Views readings in" "HTTPS"
        mobileApp -> node "Configures" "BLE"
        driver -> buffer "Stores readings in" "Function call"
        buffer -> uplink "Hands batches to" "Queue"
        uplink -> cloud "Publishes readings to" "MQTT over TLS"
        updater -> cloud "Downloads firmware from" "HTTPS"
        publisher -> session "Uses" "Function call"
        session -> cloud "Keeps the session with" "MQTT over TLS"

        deploymentEnvironment "Field" {
            deploymentNode "Sensor node hardware" "" "Cortex-M0+" {
                containerInstance driver
                containerInstance buffer
                containerInstance uplink
                containerInstance updater
            }
        }
    }

    views {
        systemContext node "SystemContext" {
            include *
            autoLayout
        }
        container node "Containers" {
            include *
            autoLayout
        }
        component uplink "Components" {
            include *
            autoLayout
        }
        dynamic node "Reading" "How one reading travels." {
            driver -> buffer "Stores reading"
            buffer -> uplink "Hands over batch"
            uplink -> cloud "Publishes batch"
            autoLayout
        }
        deployment node "Field" "FieldDeployment" {
            include *
            autoLayout
        }
        styles {
            element "Element" {
                shape RoundedBox
            }
            element "Person" {
                shape Person
            }
            element "External" {
                background #999999
            }
        }
    }
}
