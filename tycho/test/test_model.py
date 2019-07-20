from tycho.model import System

def test_system_model ():
    system = System (**{
        "name" : "test",
        "containers" : [
            {
                "name"  : "nginx-container",
                "image" : "nginx:1.9.1",
                "limits" : {
                    "cpus" : "0.5",
                    "memory" : "512M"
                }
            }
        ]
    })
    assert system.name.startswith ('test-')
    assert system.containers[0].name == 'nginx-container'
    assert system.containers[0].image == 'nginx:1.9.1'
    assert system.containers[0].limits.cpus == "0.5"
    assert system.containers[0].limits.memory == "512M"

    
