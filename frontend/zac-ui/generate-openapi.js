const fs = require('fs');
const $RefParser = require('@apidevtools/json-schema-ref-parser');

/**
 * Resolves all the references in the schema.
 * @param filePath
 * @returns {Promise<$RefParser.JSONSchema>}
 */
function resolveSchema(filePath) {
  return $RefParser.dereference(filePath, {
    resolve: {
      external: true,
    }
  });
}

try {
  const filePath = "../../backend/src/openapi.yaml";
  resolveSchema(filePath).then(schema => {
    const jsonSchema = JSON.stringify(schema);
    const outputPath = "./libs/shared/data-access/services/src/lib/openapi/schema/openapi.json"
    fs.writeFileSync(outputPath, jsonSchema);
  }).catch(e => {
    console.error(e);
  });
} catch(e) {
  console.error(e);
}
