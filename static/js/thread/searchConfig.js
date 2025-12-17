export const searchTypeToInput = {
  text: { type: "text", placeholder: "Enter a text value" },
  int: { type: "number", placeholder: "Enter an integer value" },
  float: { type: "number", placeholder: "Enter a float value", step: "any" },
  short_float: { type: "number", placeholder: "Enter a short float value", step: "any" },
  coordinate: { type: "text", placeholder: "Enter coordinates (e.g., 12.34,56.78)" },
  bool: { type: "text", placeholder: "Enter true or false" },
  date: { type: "date", placeholder: "" },
  "date-hr-sec": { type: "datetime-local", placeholder: "" },
  string: { type: "text", placeholder: "Enter a string value" },
  enum: { type: "text", placeholder: "Enter one of the enum values" }
};

