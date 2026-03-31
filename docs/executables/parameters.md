# Parameters

If in the request `is_async` is set to `False` the request will become a blocking operation. The client will not
receive a response from LSO until the executable has completed. The response then contains the output from the
executable. With `is_async` set to `True`, LSO will immediately give a response containing only the job ID. To get the
output from the excutable once completed, a callback URL must be included in the request.

## Request

When posting to the API endpoint to start an executable, the following attributes can be set.

::: lso.routes.execute.ExecutableRunParams

## Response

Once the API request is received, it returns a response that contains the following attributes.

::: lso.routes.execute.ExecutableRunResponse
