pipeline {
  parameters {
        string(name: 'PERSON', defaultValue: 'Mr Jenkins', description: 'Who should I say hello to?')
  }
  agent {
    node {
      label 'test'
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
