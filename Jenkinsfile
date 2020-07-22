pipeline {
  parameters {
        string(name: 'NODE', description: 'Where should I run??')
  }
  agent {
    node {
      label "${params.NODE}"
    }

  }
  stages {
    stage('s1') {
      steps {
        echo 'Testing'
        sh '''#! /usr/bin/env python

if __name__ == \'__main__\':
    print("Test1234")
    for i in range(100):
        print(i)'''
      }
    }

  }
}
