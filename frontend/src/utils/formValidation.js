export function getFieldError(field) {
  const { value, required, type, validity, min, max, maxLength } = field;
  if (validity.badInput) return 'Ingrese un número válido.';
  if (required && !value.trim()) return field.dataset?.requiredMessage || 'Complete este campo.';
  if (!value) return '';
  if (maxLength > 0 && value.length > maxLength) return `Ingrese hasta ${maxLength} caracteres.`;
  if (type === 'number') {
    const number = Number(value);
    if (!Number.isFinite(number)) return 'Ingrese un número válido.';
    if (min !== '' && number < Number(min)) return `Ingrese una cantidad mayor o igual a ${min}.`;
    if (max !== '' && number > Number(max)) return `La cantidad no puede superar ${max}.`;
    if (validity.stepMismatch || !Number.isSafeInteger(number)) return 'Ingrese una cantidad entera.';
  }
  if (!validity.valid) return 'Revise el valor ingresado.';
  return '';
}
