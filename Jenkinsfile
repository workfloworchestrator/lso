library 'SWDPipeline'

// Parameters:
// name (must match the name of the project in GitLab/SWD release jenkins)
String name = 'goat-lso'

// emails of people to always notify on build status changes
List<String> extraRecipients = ['erik.reid@geant.org']

// python versions (docker tags) to test against, must be explicit versions
List<String> pythonTestVersions = [g'3.11']

SimplePythonBuild(name, extraRecipients, pythonTestVersions)
