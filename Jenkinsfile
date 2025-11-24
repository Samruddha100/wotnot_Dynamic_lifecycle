pipeline {
    agent any
    
    options {
        buildDiscarder(logRotator(
            numToKeepStr: '30',
            artifactNumToKeepStr: '10',
            daysToKeepStr: '90'
        ))
        timeout(time: 1, unit: 'HOURS')
        disableConcurrentBuilds()
    }
    
    parameters {
        choice(
            name: 'ENVIRONMENT',
            choices: ['dev', 'staging', 'production'],
            description: 'Target environment for deployment'
        )
        string(
            name: 'IMAGE_TAG',
            defaultValue: '',
            description: 'Optional: Specific image tag to deploy (leave empty to use commit SHA)'
        )
        booleanParam(
            name: 'SKIP_TESTS',
            defaultValue: false,
            description: 'Skip test execution (not recommended for production)'
        )
        booleanParam(
            name: 'FORCE_DEPLOY',
            defaultValue: false,
            description: 'Force deployment even if quality gates fail (emergency only)'
        )
    }
    
    environment {
        AWS_REGION = 'ap-south-1'
        AWS_ACCOUNT_ID = '557690613541'
        ECR_REGISTRY = '557690613541.dkr.ecr.ap-south-1.amazonaws.com'
        EKS_CLUSTER_NAME = 'dynamic-pod-lifecycle'
        
        LIFECYCLE_CONTROLLER_IMAGE = '557690613541.dkr.ecr.ap-south-1.amazonaws.com/lifecycle-controller'
        API_GATEWAY_IMAGE = '557690613541.dkr.ecr.ap-south-1.amazonaws.com/api-gateway'
        SESSION_POD_IMAGE = '557690613541.dkr.ecr.ap-south-1.amazonaws.com/session-pod'
        
        GIT_COMMIT_SHORT = 'unknown'
        BUILD_TAG = 'latest'
        BRANCH_NAME = 'main'
        
        K8S_NAMESPACE = "${params.ENVIRONMENT}-sessions"
    }
    
    stages {
        stage('Checkout') {
            steps {
                script {
                    echo "Code checked out by Jenkins SCM"
                    
                    env.GIT_COMMIT_SHORT = sh(returnStdout: true, script: 'git rev-parse --short HEAD').trim()
                    env.BUILD_TAG = params.IMAGE_TAG ?: env.GIT_COMMIT_SHORT
                    env.BRANCH_NAME = sh(returnStdout: true, script: 'git rev-parse --abbrev-ref HEAD').trim()
                    
                    echo "Build Tag: ${env.BUILD_TAG}"
                    echo "Branch: ${env.BRANCH_NAME}"
                    echo "Commit: ${env.GIT_COMMIT_SHORT}"
                }
            }
        }
        
        stage('Code Quality') {
            steps {
                script {
                    echo "Running code quality checks..."
                    
                    // Verify Python tools are available (pre-installed in custom Jenkins image)
                    sh '''
                        echo "Verifying Python environment..."
                        python3 --version
                        pip3 --version || echo "pip3 not found, will use apt-installed version"
                        
                        # Use system-installed Python packages (from Dockerfile)
                        which pylint || echo "pylint not in PATH"
                        which black || echo "black not in PATH"
                        which flake8 || echo "flake8 not in PATH"
                        which pytest || echo "pytest not in PATH"
                    '''
                
                    // Run code quality checks using system-installed tools
                    sh '''
                        echo "Running pylint..."
                        pylint src/lifecycle-controller/*.py src/api-gateway/*.py src/session-pod/*.py --exit-zero --output-format=parseable > pylint-report.txt || true
                        
                        echo "Running flake8..."
                        flake8 src/ --max-line-length=120 --output-file=flake8-report.txt --exit-zero || true
                        
                        echo "Checking code formatting with black..."
                        black --check src/ || true
                    '''
                    
                    // Run tests with coverage
                    sh '''
                        echo "Running tests with coverage..."
                        cd src/lifecycle-controller
                        coverage run -m pytest test_*.py || true
                        coverage xml -o ../../coverage-lifecycle.xml || true
                        cd ../..
                        
                        cd src/api-gateway
                        coverage run -m pytest test_*.py || true
                        coverage xml -o ../../coverage-api-gateway.xml || true
                        cd ../..
                        
                        cd src/session-pod
                        coverage run -m pytest test_*.py || true
                        coverage xml -o ../../coverage-session-pod.xml || true
                        cd ../..
                    '''
                    
                    archiveArtifacts artifacts: '*-report.txt,coverage-*.xml', allowEmptyArchive: true
                }
            }
        }
        
        stage('Build') {
            steps {
                script {
                    echo "Building Docker images..."
                
                    sh """
                        echo "Building Lifecycle Controller image..."
                        docker build -t ${LIFECYCLE_CONTROLLER_IMAGE}:${BUILD_TAG} \
                            -t ${LIFECYCLE_CONTROLLER_IMAGE}:${BRANCH_NAME} \
                            -f src/lifecycle-controller/Dockerfile \
                            src/lifecycle-controller
                    """
                    
                    sh """
                        echo "Building API Gateway image..."
                        docker build -t ${API_GATEWAY_IMAGE}:${BUILD_TAG} \
                            -t ${API_GATEWAY_IMAGE}:${BRANCH_NAME} \
                            -f src/api-gateway/Dockerfile \
                            src/api-gateway
                    """
                    
                    sh """
                        echo "Building Session Pod image..."
                        docker build -t ${SESSION_POD_IMAGE}:${BUILD_TAG} \
                            -t ${SESSION_POD_IMAGE}:${BRANCH_NAME} \
                            -f src/session-pod/Dockerfile \
                            src/session-pod
                    """
                    
                    echo "Running unit tests in containers..."
                    
                    sh """
                        echo "Testing Lifecycle Controller..."
                        docker run --rm ${LIFECYCLE_CONTROLLER_IMAGE}:${BUILD_TAG} \
                            sh -c "pip install -r test_requirements.txt && pytest test_*.py -v --cov=. --cov-report=xml --cov-report=term"
                    """
                    
                    sh """
                        echo "Testing API Gateway..."
                        docker run --rm ${API_GATEWAY_IMAGE}:${BUILD_TAG} \
                            sh -c "pip install -r test_requirements.txt && pytest test_*.py -v --cov=. --cov-report=xml --cov-report=term"
                    """
                    
                    sh """
                        echo "Testing Session Pod..."
                        docker run --rm ${SESSION_POD_IMAGE}:${BUILD_TAG} \
                            sh -c "pip install -r test_requirements.txt && pytest test_*.py -v --cov=. --cov-report=xml --cov-report=term"
                    """
                    
                    echo "All images built and tested successfully!"
                    
                    sh """
                        echo "Saving Docker images as artifacts..."
                        docker save ${LIFECYCLE_CONTROLLER_IMAGE}:${BUILD_TAG} | gzip > lifecycle-controller-${BUILD_TAG}.tar.gz
                        docker save ${API_GATEWAY_IMAGE}:${BUILD_TAG} | gzip > api-gateway-${BUILD_TAG}.tar.gz
                        docker save ${SESSION_POD_IMAGE}:${BUILD_TAG} | gzip > session-pod-${BUILD_TAG}.tar.gz
                    """
                    
                    archiveArtifacts artifacts: "*-${BUILD_TAG}.tar.gz", fingerprint: true, allowEmptyArchive: false
                }
            }
        }
        
        stage('Push') {
            when {
                anyOf {
                    branch 'main'
                    branch 'develop'
                    expression { params.ENVIRONMENT == 'production' }
                }
            }
            steps {
                script {
                    echo "Pushing images to Amazon ECR..."
                
                    withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: 'aws-credentials']]) {
                        sh """
                            echo "Authenticating to ECR..."
                            aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin 557690613541.dkr.ecr.ap-south-1.amazonaws.com
                        """
                        
                        sh """
                            echo "Ensuring ECR repositories exist..."
                            aws ecr describe-repositories --repository-names lifecycle-controller --region ap-south-1 || \
                                aws ecr create-repository --repository-name lifecycle-controller --region ap-south-1
                            
                            aws ecr describe-repositories --repository-names api-gateway --region ap-south-1 || \
                                aws ecr create-repository --repository-name api-gateway --region ap-south-1
                            
                            aws ecr describe-repositories --repository-names session-pod --region ap-south-1 || \
                                aws ecr create-repository --repository-name session-pod --region ap-south-1
                        """
                        
                        sh """
                            echo "Pushing Lifecycle Controller image..."
                            docker push ${LIFECYCLE_CONTROLLER_IMAGE}:${BUILD_TAG}
                            docker push ${LIFECYCLE_CONTROLLER_IMAGE}:${BRANCH_NAME}
                        """
                        
                        sh """
                            echo "Pushing API Gateway image..."
                            docker push ${API_GATEWAY_IMAGE}:${BUILD_TAG}
                            docker push ${API_GATEWAY_IMAGE}:${BRANCH_NAME}
                        """
                        
                        sh """
                            echo "Pushing Session Pod image..."
                            docker push ${SESSION_POD_IMAGE}:${BUILD_TAG}
                            docker push ${SESSION_POD_IMAGE}:${BRANCH_NAME}
                        """
                        
                        if (env.BRANCH_NAME == 'main') {
                            sh """
                                echo "Tagging images as latest..."
                                docker tag ${LIFECYCLE_CONTROLLER_IMAGE}:${BUILD_TAG} ${LIFECYCLE_CONTROLLER_IMAGE}:latest
                                docker tag ${API_GATEWAY_IMAGE}:${BUILD_TAG} ${API_GATEWAY_IMAGE}:latest
                                docker tag ${SESSION_POD_IMAGE}:${BUILD_TAG} ${SESSION_POD_IMAGE}:latest
                                
                                docker push ${LIFECYCLE_CONTROLLER_IMAGE}:latest
                                docker push ${API_GATEWAY_IMAGE}:latest
                                docker push ${SESSION_POD_IMAGE}:latest
                            """
                        }
                        
                        sh """
                            echo "Creating image manifest..."
                            cat > image-manifest.json <<EOF
{
  "build_tag": "${BUILD_TAG}",
  "branch": "${BRANCH_NAME}",
  "commit": "${GIT_COMMIT_SHORT}",
  "timestamp": "\$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "images": {
    "lifecycle_controller": "${LIFECYCLE_CONTROLLER_IMAGE}:${BUILD_TAG}",
    "api_gateway": "${API_GATEWAY_IMAGE}:${BUILD_TAG}",
    "session_pod": "${SESSION_POD_IMAGE}:${BUILD_TAG}"
  }
}
EOF
                            cat image-manifest.json
                        """
                        
                        archiveArtifacts artifacts: 'image-manifest.json', allowEmptyArchive: false
                        
                        echo "All images pushed successfully to ECR!"
                    }
                }
            }
        }
        
        stage('Deploy') {
            when {
                anyOf {
                    branch 'main'
                    branch 'develop'
                    expression { params.ENVIRONMENT != 'dev' }
                }
            }
            steps {
                script {
                    echo "Deploying to ${params.ENVIRONMENT}..."
                
                    withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: 'aws-credentials']]) {
                        sh """
                            echo "Configuring kubectl for EKS cluster..."
                            aws eks update-kubeconfig --name dynamic-pod-lifecycle --region ap-south-1
                            kubectl config set-context --current --namespace=${K8S_NAMESPACE}
                        """
                        
                        sh """
                            echo "Ensuring namespace exists..."
                            kubectl create namespace ${K8S_NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
                        """
                        
                        sh """
                            echo "Updating image tags in manifests..."
                            mkdir -p deploy-temp
                            cp k8s-manifests/lifecycle-controller-deployment.yaml deploy-temp/
                            cp k8s-manifests/api-gateway-deployment.yaml deploy-temp/
                            sed -i "s|image:.*lifecycle-controller.*|image: ${LIFECYCLE_CONTROLLER_IMAGE}:${BUILD_TAG}|g" deploy-temp/lifecycle-controller-deployment.yaml
                            sed -i "s|image:.*api-gateway.*|image: ${API_GATEWAY_IMAGE}:${BUILD_TAG}|g" deploy-temp/api-gateway-deployment.yaml
                            sed -i "s|namespace:.*|namespace: ${K8S_NAMESPACE}|g" deploy-temp/*.yaml
                        """
                        
                        sh """
                            echo "Applying RBAC and ConfigMaps..."
                            kubectl apply -f k8s-manifests/lifecycle-controller-rbac.yaml -n ${K8S_NAMESPACE}
                            kubectl apply -f k8s-manifests/api-gateway-rbac.yaml -n ${K8S_NAMESPACE}
                            kubectl apply -f k8s-manifests/session-pod-rbac.yaml -n ${K8S_NAMESPACE}
                            kubectl apply -f k8s-manifests/lifecycle-controller-configmap.yaml -n ${K8S_NAMESPACE}
                            kubectl apply -f k8s-manifests/api-gateway-configmap.yaml -n ${K8S_NAMESPACE}
                        """
                        
                        sh """
                            echo "Applying Services..."
                            kubectl apply -f k8s-manifests/lifecycle-controller-service.yaml -n ${K8S_NAMESPACE}
                            kubectl apply -f k8s-manifests/api-gateway-service.yaml -n ${K8S_NAMESPACE}
                        """
                        
                        sh """
                            echo "Deploying applications..."
                            kubectl apply -f deploy-temp/lifecycle-controller-deployment.yaml -n ${K8S_NAMESPACE}
                            kubectl apply -f deploy-temp/api-gateway-deployment.yaml -n ${K8S_NAMESPACE}
                        """
                        
                        def rolloutSuccess = sh(
                            script: """
                                echo "Waiting for rollout to complete..."
                                kubectl rollout status deployment/lifecycle-controller -n ${K8S_NAMESPACE} --timeout=5m
                                kubectl rollout status deployment/api-gateway -n ${K8S_NAMESPACE} --timeout=5m
                            """,
                            returnStatus: true
                        )
                        
                        if (rolloutSuccess != 0) {
                            error "Deployment failed or timed out"
                        }
                        
                        sh """
                            echo "Verifying pods are running..."
                            kubectl get pods -n ${K8S_NAMESPACE}
                            kubectl get deployments -n ${K8S_NAMESPACE}
                        """
                        
                        echo "Deployment to ${params.ENVIRONMENT} completed successfully!"
                    }
                }
            }
        }
    }
    
    post {
        always {
            script {
                sh """
                    cat > build-info.txt <<EOF
Build Information
=================
Build Number: ${BUILD_NUMBER}
Build Tag: ${BUILD_TAG}
Branch: ${BRANCH_NAME}
Commit: ${GIT_COMMIT_SHORT}
Environment: ${params.ENVIRONMENT}
Timestamp: \$(date -u +%Y-%m-%dT%H:%M:%SZ)

Images Built:
- Lifecycle Controller: ${LIFECYCLE_CONTROLLER_IMAGE}:${BUILD_TAG}
- API Gateway: ${API_GATEWAY_IMAGE}:${BUILD_TAG}
- Session Pod: ${SESSION_POD_IMAGE}:${BUILD_TAG}

Build Status: ${currentBuild.result ?: 'SUCCESS'}
Build URL: ${env.BUILD_URL}
EOF
                """
                archiveArtifacts artifacts: 'build-info.txt', allowEmptyArchive: true
                
                sh 'docker image prune -f --filter "until=24h" || true'
                sh 'rm -rf deploy-temp || true'
                
                deleteDir()
            }
        }
        success {
            script {
                echo "Pipeline completed successfully!"
                echo "Build artifacts archived and available for download"
            }
        }
        failure {
            script {
                echo "Pipeline failed. Check logs for details."
                echo "Artifacts may be partially available"
            }
        }
        unstable {
            script {
                echo "Pipeline completed with warnings"
            }
        }
    }
}
