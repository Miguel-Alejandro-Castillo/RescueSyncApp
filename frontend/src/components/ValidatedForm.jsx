import { createContext, useContext, useId, useState } from 'react';
import { getFieldError } from '../utils/formValidation.js';

const ValidationContext = createContext({});

export function FieldError({ name }) {
  const { errors = {}, prefix = '' } = useContext(ValidationContext);
  return errors[name] ? <p className="field-error" id={`${prefix}-${name}-error`} role="alert">{errors[name]}</p> : null;
}

export default function ValidatedForm({ children, onSubmit, onChange, ...props }) {
  const [errors, setErrors] = useState({});
  const prefix = useId();
  function updateAccessibility(form, nextErrors) {
    for (const field of form.elements) {
      if (!field.name) continue;
      const key = field.dataset.validationKey || field.name;
      field.setAttribute('aria-invalid', Boolean(nextErrors[key]));
      const errorId = `${prefix}-${key}-error`;
      const descriptions = (field.getAttribute('aria-describedby') || '').split(/\s+/).filter(id => id && id !== errorId);
      if (nextErrors[key]) descriptions.push(errorId);
      if (descriptions.length) field.setAttribute('aria-describedby', descriptions.join(' '));
      else field.removeAttribute('aria-describedby');
    }
  }
  function handleSubmit(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const nextErrors = {};
    let firstInvalid;
    for (const field of form.elements) {
      if (!field.name || field.disabled || !field.validity) continue;
      const message = getFieldError(field);
      if (message) {
        nextErrors[field.dataset.validationKey || field.name] = message;
        firstInvalid ||= field;
      }
    }
    setErrors(nextErrors);
    updateAccessibility(form, nextErrors);
    if (firstInvalid) firstInvalid.focus();
    else onSubmit(event);
  }
  function handleChange(event) {
    const nextErrors = { ...errors };
    delete nextErrors[event.target.dataset.validationKey || event.target.name];
    setErrors(nextErrors);
    updateAccessibility(event.currentTarget, nextErrors);
    onChange?.(event);
  }
  return <ValidationContext.Provider value={{ errors, prefix }}>
    <form {...props} noValidate onSubmit={handleSubmit} onChange={handleChange}>{children}</form>
  </ValidationContext.Provider>;
}
