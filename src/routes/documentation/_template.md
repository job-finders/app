# [Route Category] Routes Documentation

## Overview

Brief description of the route category and its purpose in the platform.

## Routes

### Route Name: [HTTP_METHOD] [URL_PATTERN]

#### Metadata

- **Blueprint**: [blueprint_name]
- **Function**: [function_name]
- **Authentication**: [Required/Optional/None]
- **User Types**: [JobSeeker/Employer/Admin/Public]
- **Rate Limiting**: [Yes/No - details if applicable]

#### Description

Detailed description of what this route does and its purpose.

#### Workflow Integration

- **Job Seeker Flow**: [Where this fits in the job seeker journey]
- **Company Flow**: [Where this fits in the company/employer journey]
- **Admin Flow**: [Where this fits in the admin workflow]

#### Parameters

##### URL Parameters

- `param_name` (type): Description

##### Query Parameters

- `param_name` (type, optional/required): Description

##### Request Body

```json
{
  "field": "type - description"
}
```

#### Responses

##### Success Response

- **Status Code**: 200/201/etc.
- **Content Type**: application/json | text/html
- **Template**: [template_path] (if HTML response)

```json
{
  "example": "response"
}
```

##### Error Responses

- **Status Code**: 400/401/404/500
- **Description**: Error condition description

```json
{
  "error": "error message format"
}
```

#### Template Context (if applicable)

Variables passed to the template:

- `variable_name` (type): Description

#### Controller Integration

- **Controller**: [ControllerName]
- **Methods Used**: [controller_method_names]
- **Documentation Reference**: [link to controller documentation]

#### Security Considerations

- Authentication requirements
- Authorization checks
- Rate limiting
- Input validation

#### Examples

##### cURL Example

```bash
curl -X GET "http://localhost:8084/api/endpoint" \
  -H "Authorization: Bearer token"
```

##### JavaScript Example

```javascript
fetch('/api/endpoint', {
  method: 'GET',
  headers: {
    'Authorization': 'Bearer token'
  }
})
```

#### Related Routes

- [Related route 1]
- [Related route 2]

#### Notes

Additional implementation notes or considerations.