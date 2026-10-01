import test from 'node:test';
import assert from 'node:assert/strict';
import { getFieldError } from '../src/utils/formValidation.js';
const field = overrides => ({ value: '', required: true, type: 'text', min: '', max: '',
  maxLength: -1, validity: { valid: true, badInput: false, stepMismatch: false }, ...overrides });
test('required fields reject blanks', () => {
  assert.equal(getFieldError(field({ value: '   ' })), 'Complete este campo.');
  assert.equal(getFieldError(field({ value: 'Zona norte' })), '');
});
test('quantities validate minimum, maximum and integers', () => {
  assert.match(getFieldError(field({ type: 'number', min: '1', value: '0' })), /mayor o igual a 1/);
  assert.match(getFieldError(field({ type: 'number', max: '5', value: '6' })), /superar 5/);
  assert.equal(getFieldError(field({ type: 'number', value: '1.5' })), 'Ingrese una cantidad entera.');
  assert.equal(getFieldError(field({ type: 'number', value: 'abc' })), 'Ingrese un número válido.');
  assert.equal(getFieldError(field({ type: 'number', min: '1', max: '5', value: '5' })), '');
});
test('text lengths match backend limits', () => {
  assert.equal(getFieldError(field({ maxLength: 3, value: 'abcd' })), 'Ingrese hasta 3 caracteres.');
});
