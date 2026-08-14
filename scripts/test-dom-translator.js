// Test funcional de la lógica DOM del traductor en tiempo real.
// Replica scanTranslate/scanRestore/translateTextNode de i18n-context.tsx
// (estado guardado en el propio nodo de texto) con un mock mínimo de DOM.

const { translateToEnglish } = require('../src/.tmp-test/runtime-translator.js');

// --- Mock mínimo de DOM ---
class MockEl {
  constructor(text) {
    this.tagName = 'DIV';
    this.parentElement = null;
    this.children = [];
    if (text !== undefined) this.appendChild(new MockText(text, this));
  }
  appendChild(node) { node.parentElement = this; this.children.push(node); return node; }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  removeAttribute(k) { delete this.attrs[k]; }
  hasAttribute(k) { return k in this.attrs; }
  get nodeType() { return 1; }
  get textContent() { return this.children.map((c) => (c.nodeType === 3 ? c.nodeValue ?? '' : c.textContent)).join(''); }
}

class MockText {
  constructor(value, parent) { this.nodeValue = value; this.parentElement = parent ?? null; }
  get nodeType() { return 3; }
}

function collectTextNodes(root, out = []) {
  for (const child of root.children ?? []) {
    if (child.nodeType === 3) out.push(child);
    else collectTextNodes(child, out);
  }
  return out;
}

// Misma lógica que i18n-context.tsx
const SKIP_TAGS = new Set(['SCRIPT', 'STYLE', 'TEXTAREA', 'INPUT', 'SELECT', 'OPTION', 'CODE', 'PRE', 'KBD', 'SVG']);

function shouldSkip(node) {
  const parent = node.parentElement;
  if (!parent) return true;
  if (SKIP_TAGS.has(parent.tagName)) return true;
  let el = parent;
  let depth = 0;
  while (el && depth < 4) {
    if (SKIP_TAGS.has(el.tagName)) return true;
    el = el.parentElement;
    depth++;
  }
  return false;
}

function translateTextNode(node) {
  const text = node.nodeValue ?? '';
  if (!text.trim()) return;
  if (text.length > 500) return;
  if (!node.parentElement) return;
  const rt = node;
  if (rt.__rtEn !== undefined) {
    if (text === rt.__rtEn) return;
    rt.__rtEs = undefined;
    rt.__rtEn = undefined;
  }
  const translated = translateToEnglish(text);
  if (translated === text) return;
  rt.__rtEs = text;
  rt.__rtEn = translated;
  node.nodeValue = translated;
}

function restoreTextNode(node) {
  const rt = node;
  if (rt.__rtEs !== undefined) node.nodeValue = rt.__rtEs;
  rt.__rtEs = undefined;
  rt.__rtEn = undefined;
}

function scanTranslate(root) {
  for (const tn of collectTextNodes(root)) {
    if (!shouldSkip(tn)) translateTextNode(tn);
  }
}

function scanRestore(root) {
  for (const tn of collectTextNodes(root)) restoreTextNode(tn);
}

let failures = 0;
function check(name, actual, expected) {
  const ok = actual === expected;
  if (!ok) failures++;
  console.log(`${ok ? '✅' : '❌'} ${name}: ${JSON.stringify(actual)}${ok ? '' : ' (esperado: ' + JSON.stringify(expected) + ')'}`);
}

// 1. Traducir al inglés
const body = new MockEl();
const nav = new MockEl(); body.appendChild(nav);
nav.appendChild(new MockText('Nueva Factura'));
const span = new MockEl(); body.appendChild(span);
span.appendChild(new MockText('Guardar cambios'));
const inputWrap = new MockEl(); inputWrap.tagName = 'INPUT'; body.appendChild(inputWrap);
inputWrap.appendChild(new MockText('Contraseña'));

scanTranslate(body);
check('Traduce texto visible', span.textContent, 'Save changes');
check('Traduce navegación', nav.textContent, 'New Invoice');
check('Input no se traduce', inputWrap.textContent, 'Contraseña');

// 2. React re-renderiza con texto NUEVO en español en el mismo nodo -> re-traduce
span.children[0].nodeValue = 'Eliminar producto';
scanTranslate(body);
check('Re-render con texto nuevo se re-traduce', span.textContent, 'Delete product');

// 3. React re-renderiza con el MISMO texto español -> re-traduce de nuevo (sigue en inglés)
span.children[0].nodeValue = 'Eliminar producto';
scanTranslate(body);
check('Mismo español de nuevo -> se mantiene traducido', span.textContent, 'Delete product');

// 4. Nodo con texto mixto (elemento con 2 nodos de texto, p. ej. "Hola {name}")
const mixed = new MockEl(); body.appendChild(mixed);
mixed.appendChild(new MockText('Cliente: '));
const strong = new MockEl(); mixed.appendChild(strong);
strong.appendChild(new MockText('María'));
mixed.appendChild(new MockText(' - Total'));
scanTranslate(body);
check('Texto mixto se traduce por nodo', mixed.textContent, 'Customer: María - Total');

// 5. Restaurar al español
scanRestore(body);
check('Restaura navegación', nav.textContent, 'Nueva Factura');
check('Restaura nodo re-traducido', span.textContent, 'Eliminar producto');
check('Restaura mixto', mixed.textContent, 'Cliente: María - Total');

// 6. Volver a traducir tras restaurar
scanTranslate(body);
check('Re-traduce tras restaurar', span.textContent, 'Delete product');

console.log(failures === 0 ? '\n🎉 TODAS LAS PRUEBAS PASARON' : `\n❌ ${failures} PRUEBAS FALLARON`);
process.exit(failures === 0 ? 0 : 1);
