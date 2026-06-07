import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

Object.defineProperty(globalThis, "localStorage", {
  configurable: true,
  value: window.localStorage ?? createMemoryStorage(),
});

Object.defineProperty(window, "matchMedia", {
  configurable: true,
  value: (query: string) => ({
    addEventListener: vi.fn(),
    addListener: vi.fn(),
    dispatchEvent: vi.fn(),
    matches: false,
    media: query,
    onchange: null,
    removeEventListener: vi.fn(),
    removeListener: vi.fn(),
  }),
});

class ResizeObserver {
  constructor(private readonly callback: ResizeObserverCallback) {}

  observe(target: Element) {
    queueMicrotask(() => {
      this.callback([{ target } as ResizeObserverEntry], this);
    });
  }

  unobserve() {}
  disconnect() {}
}

Object.defineProperty(window, "ResizeObserver", {
  configurable: true,
  value: ResizeObserver,
});

Object.defineProperty(globalThis, "ResizeObserver", {
  configurable: true,
  value: ResizeObserver,
});

class DOMMatrixReadOnly {
  readonly m22 = 1;
}

Object.defineProperty(window, "DOMMatrixReadOnly", {
  configurable: true,
  value: DOMMatrixReadOnly,
});

Object.defineProperty(HTMLElement.prototype, "offsetWidth", {
  configurable: true,
  get() {
    return this.classList.contains("task-node-handle") ? 9 : 280;
  },
});

Object.defineProperty(HTMLElement.prototype, "offsetHeight", {
  configurable: true,
  get() {
    return this.classList.contains("task-node-handle") ? 9 : 150;
  },
});

HTMLElement.prototype.getBoundingClientRect = function () {
  const width = this.offsetWidth;
  const height = this.offsetHeight;

  return {
    bottom: height,
    height,
    left: 0,
    right: width,
    top: 0,
    width,
    x: 0,
    y: 0,
    toJSON: () => ({}),
  };
};

function createMemoryStorage(): Storage {
  const entries = new Map<string, string>();

  return {
    get length() {
      return entries.size;
    },
    clear() {
      entries.clear();
    },
    getItem(key: string) {
      return entries.get(key) ?? null;
    },
    key(index: number) {
      return Array.from(entries.keys())[index] ?? null;
    },
    removeItem(key: string) {
      entries.delete(key);
    },
    setItem(key: string, value: string) {
      entries.set(key, value);
    },
  };
}
