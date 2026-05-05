// Manual mock for src/render.jsx
// Re-exports useAppContext backed by the test AppContext so components
// rendered via renderWithProviders(…) receive the correct context values.
export { useAppContext } from '../test/test-utils.jsx';
export default vi.fn();
