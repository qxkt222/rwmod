/**
 * Simple reactive store — publish/subscribe state management.
 *
 * Usage:
 *   const store = createStore({ count: 0 });
 *   store.subscribe("count", (val) => console.log(val));
 *   store.set("count", 5);  // triggers subscriber
 */

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Listener<T> = (val: T) => void;

class Store<T extends Record<string, unknown>> {
  private _state: T;
  private _listeners = new Map<keyof T, Set<Listener<unknown>>>();

  constructor(initial: T) {
    this._state = { ...initial };
  }

  get<K extends keyof T>(key: K): T[K] {
    return this._state[key];
  }

  set<K extends keyof T>(key: K, val: T[K]): void {
    this._state[key] = val;
    this._listeners.get(key)?.forEach((fn) => fn(val));
  }

  /** Immutable update: replace the entire state object */
  update(partial: Partial<T>): void {
    Object.assign(this._state, partial);
    for (const key of Object.keys(partial) as (keyof T)[]) {
      this._listeners.get(key)?.forEach((fn) => fn(this._state[key]));
    }
  }

  subscribe<K extends keyof T>(key: K, fn: Listener<T[K]>): () => void {
    if (!this._listeners.has(key)) this._listeners.set(key, new Set());
    this._listeners.get(key)!.add(fn as Listener<unknown>);
    return () => this._listeners.get(key)?.delete(fn as Listener<unknown>);
  }

  snapshot(): Readonly<T> {
    return { ...this._state };
  }
}

export interface AppState {
  mods: ModEntry[];
  queue: QueueItem[];
  config: ConfigData | null;
  online: boolean;
  darkMode: boolean;
  currentPanel: string;
}

export interface ModEntry {
  folder: string;
  name: string;
  package_id: string;
  workshop_id: string;
}

export interface QueueItem {
  id: string;
  name: string;
  status: string;
  progress: number;
  msg: string;
}

export interface ConfigData {
  steamcmd_path: string;
  mods_dir: string;
  rimworld_dir: string;
  backup_dir: string;
  steamcmd_exists: boolean;
  mods_dir_exists: boolean;
}

/** Global application store */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const store = new Store<AppState & Record<string, any>>({
  mods: [],
  queue: [],
  config: null,
  online: true,
  darkMode: false,
  currentPanel: "dashboard",
});

export { Store };
