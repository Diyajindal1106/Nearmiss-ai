import { createContext, useContext, useEffect, useState } from "react";
import { api } from "./api.js";

const Ctx = createContext({ config: null, error: null });
export const useConfig = () => useContext(Ctx);

export function ConfigProvider({ children }) {
  const [state, setState] = useState({ config: null, error: null });
  useEffect(() => {
    api
      .config()
      .then((config) => setState({ config, error: null }))
      .catch((e) => setState({ config: null, error: e.message }));
  }, []);
  return <Ctx.Provider value={state}>{children}</Ctx.Provider>;
}
