!const PRODUCT_NAME "Portal Dados Gov"

workspace "${PRODUCT_NAME} Infrastructure" {
    model {
        ss = softwareSystem "${PRODUCT_NAME}" "${PRODUCT_NAME} Infrastructure" {
            aksclusternode = container "AKS Cluster Node" "" "" "Kubernetes - node"
            k8singress = container "Kubernetes Ingress" "" "" "Kubernetes - ing"

            k8singress -> aksclusternode "Route incomming cluster traffic"

            udata-fe = container "udata-fe" "" "" "Kubernetes - pod"
            nodejs-app = container "nodejs-app" "" "" "Kubernetes - pod"
            udata-be = container "udata-be" "" "" "Kubernetes - pod"
            mongo-db = container "mongo-db" "" "" "Kubernetes - pod"
            hydra-app = container "hydra-app" "" "" "Kubernetes - pod"
            hydra-postgres = container "hydra-postgres" "" "" "Kubernetes - pod"
            hydra-postgres-csv = container "hydra-postgres-csv" "" "" "Kubernetes - pod"
            tabular-api = container "tabular-api" "" "" "Kubernetes - pod"
            metrics-api = container "metrics-api" "" "" "Kubernetes - pod"
            postgrest = container "postgrest" "" "" "Kubernetes - pod"
            airflow-app = container "airflow-app" "" "" "Kubernetes - pod"
            airflow-scheduler = container "airflow-scheduler" "" "" "Kubernetes - pod"
            airflow-worker = container "airflow-worker" "" "" "Kubernetes - pod"
            airflow-flower = container "airflow-flower" "" "" "Kubernetes - pod"
            airflow-triggerer = container "airflow-triggerer" "" "" "Kubernetes - pod"
            airflow-postgres = container "airflow-postgres" "" "" "Kubernetes - pod"
            redis = container "redis" "" "" "Kubernetes - pod"
            elasticsearch = container "elasticsearch" "" "" "Kubernetes - pod"
            kibana = container "kibana" "" "" "Kubernetes - pod"
        }
        development = deploymentEnvironment "Development" {
            deploymentNode "Subscription" {
                publicadordev = infrastructureNode "Publicador" "" "" "largetext" {
                    description "Receives ->\n - dados.dev.ic.ama.lan\n - airflow-dados.dev.ic.ama.lan\n - kibana-dados.dev.ic.ama.lan\n \nRedirects ->\n - ingress.dev.ic.ama.lan"
                }

                tags "Microsoft Azure - Subscriptions"
            }
            deploymentNode "Development - DEV - Environment" {
                sncicddev = infrastructureNode "spk-DevOps-CICD-route-subnet-dev" "" "" "Microsoft Azure - Route Tables"

                deploymentNode "AKS Cluster DEV" "" "" "Kubernetes - node" {
                    k8singressdev = containerInstance k8singress {
                        description "ingress.dev.ic.ama.lan"
                    }

                    aksclusternodedev = containerInstance aksclusternode

                    deploymentNode "dev-dados Namespace" "" "" "Kubernetes - ns" {
                        containerInstance udata-fe "" "largetext" {
                            description "dados.dev.ic.ama.lan"
                        }
                        containerInstance nodejs-app "" "largetext" {
                            description "be-nodejs-service.dev-dados.svc.cluster.local"
                        }
                        containerInstance udata-be "" "largetext" {
                            description "be-udata-service.dev-dados.svc.cluster.local"
                        }
                        containerInstance mongo-db "" "largetext" {
                            description "mongo-db-service.dev-dados.svc.cluster.local"
                        }
                        containerInstance hydra-app "" "largetext" {
                            description "hydra-service.dev-dados.svc.cluster.local"
                        }
                        containerInstance hydra-postgres "" "largetext" {
                            description "hydra-postgres-service.dev-dados.svc.cluster.local"
                        }
                        containerInstance hydra-postgres-csv "" "largetext" {
                            description "hydra-postgres-csv-service.dev-dados.svc.cluster.local"
                        }
                        containerInstance tabular-api "" "largetext" {
                            description "tabular-api-service.dev-dados.svc.cluster.local"
                        }
                        containerInstance metrics-api "" "largetext" {
                            description "metrics-api-service.dev-dados.svc.cluster.local"
                        }
                        containerInstance postgrest "" "largetext" {
                            description "postgrest-service.dev-dados.svc.cluster.local"
                        }
                        containerInstance airflow-app "" "largetext" {
                            description "airflow-dados.dev.ic.ama.lan"
                        }
                        containerInstance airflow-scheduler "" "largetext" {
                            description ""
                        }
                        containerInstance airflow-worker "" "largetext" {
                            description ""
                        }
                        containerInstance airflow-flower "" "largetext" {
                            description ""
                        }
                        containerInstance airflow-triggerer "" "largetext" {
                            description ""
                        }
                        containerInstance airflow-postgres "" "largetext" {
                            description "airflow-postgres-service.dev-dados.svc.cluster.local"
                        }
                        containerInstance redis "" "largetext" {
                            description "redis-service.dev-dados.svc.cluster.local"
                        }
                        containerInstance elasticsearch "" "largetext" {
                            description "elasticsearch-service.dev-dados.svc.cluster.local"
                        }
                        containerInstance kibana "" "largetext" {
                            description "kibana-dados.dev.ic.ama.lan"
                        }
                    }
                }

                tags "Microsoft Azure - Resource Groups"
            }

            publicadordev -> k8singressdev "Forwards requests to ingress.dev.ic.ama.lan" "HTTP" {
                tags "continuousarrowfromoutside"
            }
        }
        test = deploymentEnvironment "Test" {
            deploymentNode "Subscription" {
                publicadortst = infrastructureNode "Publicador" "" "" "largetext" {
                    description "Receives ->\n - dados.tst.ic.ama.lan\n - airflow-dados.tst.ic.ama.lan\n - kibana-dados.tst.ic.ama.lan\n \nRedirects ->\n - ingress.tst.ic.ama.lan"
                }

                tags "Microsoft Azure - Subscriptions"
            }
            deploymentNode "Test - TST - Environment" {
                sncicdtst = infrastructureNode "spk-DevOps-CICD-route-subnet-tst" "" "" "Microsoft Azure - Route Tables"

                deploymentNode "AKS Cluster TST" "" "" "Kubernetes - node" {
                    k8singresstst = containerInstance k8singress {
                        description "ingress.tst.ic.ama.lan"
                    }

                    aksclusternodetst = containerInstance aksclusternode

                    deploymentNode "tst-dados Namespace" "" "" "Kubernetes - ns" {
                        containerInstance udata-fe "" "largetext" {
                            description "dados.tst.ic.ama.lan"
                        }
                        containerInstance nodejs-app "" "largetext" {
                            description "be-nodejs-service.tst-dados.svc.cluster.local"
                        }
                        containerInstance udata-be "" "largetext" {
                            description "be-udata-service.tst-dados.svc.cluster.local"
                        }
                        containerInstance mongo-db "" "largetext" {
                            description "mongo-db-service.tst-dados.svc.cluster.local"
                        }
                        containerInstance hydra-app "" "largetext" {
                            description "hydra-service.tst-dados.svc.cluster.local"
                        }
                        containerInstance hydra-postgres "" "largetext" {
                            description "hydra-postgres-service.tst-dados.svc.cluster.local"
                        }
                        containerInstance hydra-postgres-csv "" "largetext" {
                            description "hydra-postgres-csv-service.tst-dados.svc.cluster.local"
                        }
                        containerInstance tabular-api "" "largetext" {
                            description "tabular-api-service.tst-dados.svc.cluster.local"
                        }
                        containerInstance metrics-api "" "largetext" {
                            description "metrics-api-service.tst-dados.svc.cluster.local"
                        }
                        containerInstance postgrest "" "largetext" {
                            description "postgrest-service.tst-dados.svc.cluster.local"
                        }
                        containerInstance airflow-app "" "largetext" {
                            description "airflow-dados.tst.ic.ama.lan"
                        }
                        containerInstance airflow-scheduler "" "largetext" {
                            description ""
                        }
                        containerInstance airflow-worker "" "largetext" {
                            description ""
                        }
                        containerInstance airflow-flower "" "largetext" {
                            description ""
                        }
                        containerInstance airflow-triggerer "" "largetext" {
                            description ""
                        }
                        containerInstance airflow-postgres "" "largetext" {
                            description "airflow-postgres-service.tst-dados.svc.cluster.local"
                        }
                        containerInstance redis "" "largetext" {
                            description "redis-service.tst-dados.svc.cluster.local"
                        }
                        containerInstance elasticsearch "" "largetext" {
                            description "elasticsearch-service.tst-dados.svc.cluster.local"
                        }
                        containerInstance kibana "" "largetext" {
                            description "kibana-dados.tst.ic.ama.lan"
                        }
                    }
                }

                tags "Microsoft Azure - Resource Groups"
            }

            publicadortst -> k8singresstst "Forwards requests to ingress.tst.ic.ama.lan" "HTTP" {
                tags "continuousarrowfromoutside"
            }
        }
        preproduction = deploymentEnvironment "Pre-Production" {
            deploymentNode "Subscription" {
                publicadorppr = infrastructureNode "Publicador" "" "" "largetext" {
                    description "Receives ->\n - ppr.dados.gov.pt\n - dados.ppr.ic.ama.lan\n - be-dados.ppr.ic.ama.lan\n - ppr-ee.dados.gov.pt\n - airflow-dados.ppr.ic.ama.lan\n - kibana-dados.ppr.ic.ama.lan\n \nRedirects ->\n - ingress.ppr.ic.ama.lan"
                }

                tags "Microsoft Azure - Subscriptions"
            }
            deploymentNode "Pre-Production - PPR - Environment" {
                sncicdppr = infrastructureNode "spk-DevOps-CICD-route-subnet-ppr" "" "" "Microsoft Azure - Route Tables"

                deploymentNode "AKS Cluster PPR" "" "" "Kubernetes - node" {
                    k8singressppr = containerInstance k8singress {
                        description "ingress.ppr.ic.ama.lan"
                    }

                    aksclusternodeppr = containerInstance aksclusternode

                    deploymentNode "ppr-dados Namespace" "" "" "Kubernetes - ns" {
                        containerInstance udata-fe "" "largetext" {
                            description "ppr.dados.gov.pt\n dados.ppr.ic.ama.lan"
                        }
                        containerInstance nodejs-app "" "largetext" {
                            description "be-dados.ppr.ic.ama.lan"
                        }
                        containerInstance udata-be "" "largetext" {
                            description "be-udata-service.ppr-dados.svc.cluster.local"
                        }
                        containerInstance mongo-db "" "largetext" {
                            description "mongo-db-service.ppr-dados.svc.cluster.local"
                        }
                        containerInstance hydra-app "" "largetext" {
                            description "hydra-service.ppr-dados.svc.cluster.local"
                        }
                        containerInstance hydra-postgres "" "largetext" {
                            description "hydra-postgres-service.ppr-dados.svc.cluster.local"
                        }
                        containerInstance hydra-postgres-csv "" "largetext" {
                            description "hydra-postgres-csv-service.ppr-dados.svc.cluster.local"
                        }
                        containerInstance tabular-api "" "largetext" {
                            description "tabular-api-service.ppr-dados.svc.cluster.local"
                        }
                        containerInstance metrics-api "" "largetext" {
                            description "metrics-api-service.ppr-dados.svc.cluster.local"
                        }
                        containerInstance postgrest "" "largetext" {
                            description "postgrest-service.ppr-dados.svc.cluster.local"
                        }
                        containerInstance airflow-app "" "largetext" {
                            description "airflow-dados.ppr.ic.ama.lan"
                        }
                        containerInstance airflow-scheduler "" "largetext" {
                            description ""
                        }
                        containerInstance airflow-worker "" "largetext" {
                            description ""
                        }
                        containerInstance airflow-flower "" "largetext" {
                            description ""
                        }
                        containerInstance airflow-triggerer "" "largetext" {
                            description ""
                        }
                        containerInstance airflow-postgres "" "largetext" {
                            description "airflow-postgres-service.ppr-dados.svc.cluster.local"
                        }
                        containerInstance redis "" "largetext" {
                            description "redis-service.ppr-dados.svc.cluster.local"
                        }
                        containerInstance elasticsearch "" "largetext" {
                            description "elasticsearch-service.ppr-dados.svc.cluster.local\n ppr-ee.dados.gov.pt"
                        }
                        containerInstance kibana "" "largetext" {
                            description "kibana-dados.ppr.ic.ama.lan"
                        }
                    }
                }

                tags "Microsoft Azure - Resource Groups"
            }

            publicadorppr -> k8singressppr "Forwards requests to ingress.ppr.ic.ama.lan" "HTTP" {
                tags "continuousarrowfromoutside"
            }
        }
        production = deploymentEnvironment "Production" {
            deploymentNode "Subscription" {
                publicadorprd = infrastructureNode "Publicador" "" "" "largetext" {
                    description "Receives ->\n - dados.gov.pt\n - dados.prd.ic.ama.lan\n - be-dados.prd.ic.ama.lan\n - airflow-dados.prd.ic.ama.lan\n - kibana-dados.prd.ic.ama.lan\n \nRedirects ->\n - ingress.prd.ic.ama.lan"
                }

                tags "Microsoft Azure - Subscriptions"
            }
            deploymentNode "Production - PRD - Environment" {
                sncicdprd = infrastructureNode "spk-DevOps-CICD-route-subnet-prd" "" "" "Microsoft Azure - Route Tables"

                deploymentNode "AKS Cluster PRD" "" "" "Kubernetes - node" {
                    k8singressprd = containerInstance k8singress {
                        description "ingress.prd.ic.ama.lan"
                    }

                    aksclusternodeprd = containerInstance aksclusternode

                    deploymentNode "prd-dados Namespace" "" "" "Kubernetes - ns" {
                        containerInstance udata-fe "" "largetext" {
                            description "dados.gov.pt\n dados.prd.ic.ama.lan"
                        }
                        containerInstance nodejs-app "" "largetext" {
                            description "be-dados.prd.ic.ama.lan"
                        }
                        containerInstance udata-be "" "largetext" {
                            description "be-udata-service.prd-dados.svc.cluster.local"
                        }
                        containerInstance mongo-db "" "largetext" {
                            description "mongo-db-service.prd-dados.svc.cluster.local"
                        }
                        containerInstance hydra-app "" "largetext" {
                            description "hydra-service.prd-dados.svc.cluster.local"
                        }
                        containerInstance hydra-postgres "" "largetext" {
                            description "hydra-postgres-service.prd-dados.svc.cluster.local"
                        }
                        containerInstance hydra-postgres-csv "" "largetext" {
                            description "hydra-postgres-csv-service.prd-dados.svc.cluster.local"
                        }
                        containerInstance tabular-api "" "largetext" {
                            description "tabular-api-service.prd-dados.svc.cluster.local"
                        }
                        containerInstance metrics-api "" "largetext" {
                            description "metrics-api-service.prd-dados.svc.cluster.local"
                        }
                        containerInstance postgrest "" "largetext" {
                            description "postgrest-service.prd-dados.svc.cluster.local"
                        }
                        containerInstance airflow-app "" "largetext" {
                            description "airflow-dados.prd.ic.ama.lan"
                        }
                        containerInstance airflow-scheduler "" "largetext" {
                            description ""
                        }
                        containerInstance airflow-worker "" "largetext" {
                            description ""
                        }
                        containerInstance airflow-flower "" "largetext" {
                            description ""
                        }
                        containerInstance airflow-triggerer "" "largetext" {
                            description ""
                        }
                        containerInstance airflow-postgres "" "largetext" {
                            description "airflow-postgres-service.prd-dados.svc.cluster.local"
                        }
                        containerInstance redis "" "largetext" {
                            description "redis-service.prd-dados.svc.cluster.local"
                        }
                        containerInstance elasticsearch "" "largetext" {
                            description "elasticsearch-service.prd-dados.svc.cluster.local"
                        }
                        containerInstance kibana "" "largetext" {
                            description "kibana-dados.prd.ic.ama.lan"
                        }
                    }
                }

                tags "Microsoft Azure - Resource Groups"
            }

            publicadorprd -> k8singressprd "Forwards requests to ingress.prd.ic.ama.lan" "HTTP" {
                tags "continuousarrowfromoutside"
            }
        }
    }

    views {
        deployment ss development {
            title "${PRODUCT_NAME} - Development Environment"
            description "Default Kubernetes Cloud DEV environment"
            include *
            autoLayout tb
        }
        deployment ss test {
            title "${PRODUCT_NAME} - Test Environment"
            description "Default Kubernetes Cloud TST environment"
            include *
            autoLayout tb
        }
        deployment ss preproduction {
            title "${PRODUCT_NAME} - Pre-Production Environment"
            description "Default Kubernetes Cloud PPR environment"
            include *
            autoLayout tb
        }
        deployment ss production {
            title "${PRODUCT_NAME} - Production Environment"
            description "Default Kubernetes Cloud PRD environment"
            include *
            autoLayout tb
        }
        container ss {
            title "${PRODUCT_NAME} - Container View"
            description "General Container view for ${PRODUCT_NAME}"
            include element.type==container
            autoLayout lr
        }

        themes https://static.structurizr.com/themes/microsoft-azure-2023.01.24/theme.json https://static.structurizr.com/themes/kubernetes-v0.3/theme.json

        styles {
            relationship "continuousarrow" {
                dashed false
                color #808000
            }
            relationship "continuousarrowfromoutside" {
                dashed false
                color #1966FF
            }
            element "filler" {
                width 1
                height 1
                description false
                metadata false
                opacity 100
            }
            element "Deployment Node" {
                metadata true
            }
            element "largetext" {
                width 900
                height 500
            }
            element "External System" {
                background #F0F0F0
                color #000000
                shape hexagon
            }
            element "ExternalSystemLargeText" {
                background #F0F0F0
                color #000000
                shape hexagon
                width 900
                height 500
                fontSize 12
            }
            element "restricted-network-access" {
                color #ff7133
            }
            element "emptyelement" {
                width 400
                height 250
                description false
                metadata false
                opacity 100
            }
            element "largetext-notinuse" {
                width 900
                height 500
                color #ff5733
            }
        }
    }
}
