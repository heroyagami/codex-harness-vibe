const getStaticPropertyName = (property) => {
  if (property.type !== "Property") {
    return null;
  }

  if (!property.computed && property.key.type === "Identifier") {
    return property.key.name;
  }

  if (
    property.key.type === "Literal" &&
    typeof property.key.value === "string"
  ) {
    return property.key.value;
  }

  return null;
};

const unwrapExpression = (expression) => {
  let current = expression;

  while (
    current &&
    [
      "ChainExpression",
      "TSAsExpression",
      "TSNonNullExpression",
      "TSSatisfiesExpression",
      "TSTypeAssertion",
    ].includes(current.type)
  ) {
    current = current.expression;
  }

  return current;
};

const findVariable = (scope, name) => {
  let current = scope;

  while (current) {
    const variable = current.set.get(name);

    if (variable) {
      return variable;
    }

    current = current.upper;
  }

  return null;
};

const getConstInitializer = (variable) => {
  const definitions = variable.defs.filter(
    (definition) =>
      definition.type === "Variable" &&
      definition.parent?.kind === "const" &&
      definition.node.id.type === "Identifier" &&
      definition.node.id.name === variable.name,
  );

  return definitions.length === 1 ? definitions[0].node.init : null;
};

const resolveStaticStyleObject = (expression, sourceCode, seen = new Set()) => {
  const current = unwrapExpression(expression);

  if (current?.type === "ObjectExpression") {
    return current;
  }

  if (current?.type !== "Identifier") {
    return null;
  }

  const variable = findVariable(sourceCode.getScope(current), current.name);

  if (!variable || seen.has(variable)) {
    return null;
  }

  const initializer = getConstInitializer(variable);

  if (!initializer) {
    return null;
  }

  seen.add(variable);
  return resolveStaticStyleObject(initializer, sourceCode, seen);
};

export default {
  meta: {
    type: "problem",
    docs: {
      description:
        "require an explicit flexDirection for statically known AbsoluteFill flex alignment",
    },
    schema: [],
    messages: {
      missingFlexDirection:
        "Declare flexDirection in this AbsoluteFill style when using alignItems or justifyContent.",
    },
  },
  create(context) {
    const sourceCode = context.sourceCode;

    return {
      JSXOpeningElement(node) {
        if (
          node.name.type !== "JSXIdentifier" ||
          node.name.name !== "AbsoluteFill"
        ) {
          return;
        }

        for (const attribute of node.attributes) {
          if (
            attribute.type !== "JSXAttribute" ||
            attribute.name.type !== "JSXIdentifier" ||
            attribute.name.name !== "style" ||
            attribute.value?.type !== "JSXExpressionContainer"
          ) {
            continue;
          }

          const style = resolveStaticStyleObject(
            attribute.value.expression,
            sourceCode,
          );

          if (style?.type !== "ObjectExpression") {
            continue;
          }

          const propertyNames = new Set(
            style.properties.map(getStaticPropertyName).filter(Boolean),
          );
          const usesFlexAlignment =
            propertyNames.has("alignItems") ||
            propertyNames.has("justifyContent");

          if (usesFlexAlignment && !propertyNames.has("flexDirection")) {
            context.report({
              node: attribute,
              messageId: "missingFlexDirection",
            });
          }
        }
      },
    };
  },
};
