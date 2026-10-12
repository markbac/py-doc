workspace "Meter Gateway" "Reads meters and reports to the head-end." {

    model {
        installer = person "Installer" "Installs and commissions gateways."
        headEnd = softwareSystem "Head-end System" "Collects readings from all gateways." "External"

        gateway = softwareSystem "Meter Gateway" "Reads meters and sends readings to the head-end." {
            reader = container "Reader" "Polls the meter." "C, FreeRTOS"
            buffer = container "Buffer" "Keeps readings while the network is down." "SQLite on flash"
            uplink = container "Uplink" "Sends readings." "C, LwM2M over DTLS" {
                session = component "Session Manager" "Keeps the DTLS session alive." "C"
            }
        }

        installer -> gateway "Commissions using" "USB"
        reader -> buffer "Stores readings in" "SQL"
        buffer -> uplink "Hands batches to" "Queue"
        uplink -> headEnd "Sends readings to" "LwM2M over DTLS"

        deploymentEnvironment "Field" {
            deploymentNode "Gateway hardware" "" "Cortex-M4" {
                containerInstance reader
                containerInstance buffer
                containerInstance uplink
            }
        }
    }

    views {
        systemContext gateway "SystemContext" {
            include *
            autoLayout
        }
        container gateway "Containers" {
            include *
            autoLayout
        }
        component uplink "Components" {
            include *
            autoLayout
        }
        dynamic gateway "Reading" "How one reading travels." {
            reader -> buffer "Stores reading"
            buffer -> uplink "Hands over batch"
            uplink -> headEnd "Sends batch"
            autoLayout
        }
        deployment gateway "Field" "FieldDeployment" {
            include *
            autoLayout
        }
        styles {
            element "Element" {
                shape RoundedBox
            }
            element "External" {
                background #999999
            }
        }
    }
}
