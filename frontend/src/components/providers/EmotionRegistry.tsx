"use client";

import { useState, type ReactNode } from "react";
import createCache from "@emotion/cache";
import { CacheProvider } from "@emotion/react";
import { useServerInsertedHTML } from "next/navigation";

/**
 * Collects the Emotion styles generated while server-rendering and injects them into the
 * streamed HTML, so MUI styles match on hydration in the App Router.
 */
export function EmotionRegistry({ children }: { children: ReactNode }) {
  const [registry] = useState(() => {
    const cache = createCache({ key: "mui" });
    cache.compat = true;
    const originalInsert = cache.insert;
    let inserted: { name: string; isGlobal: boolean }[] = [];
    cache.insert = (...args: Parameters<typeof originalInsert>) => {
      const [selector, serialized] = args;
      if (cache.inserted[serialized.name] === undefined) {
        inserted.push({ name: serialized.name, isGlobal: !selector });
      }
      return originalInsert(...args);
    };
    const flush = () => {
      const flushed = inserted;
      inserted = [];
      return flushed;
    };
    return { cache, flush };
  });

  useServerInsertedHTML(() => {
    const names = registry.flush();
    if (names.length === 0) return null;

    let styles = "";
    let dataEmotionAttribute = registry.cache.key;
    const globals: ReactNode[] = [];

    for (const { name, isGlobal } of names) {
      const style = registry.cache.inserted[name];
      if (typeof style !== "string") continue;
      if (isGlobal) {
        globals.push(
          <style
            key={name}
            data-emotion={`${registry.cache.key}-global ${name}`}
            dangerouslySetInnerHTML={{ __html: style }}
          />,
        );
      } else {
        styles += style;
        dataEmotionAttribute += ` ${name}`;
      }
    }

    return (
      <>
        {globals}
        <style data-emotion={dataEmotionAttribute} dangerouslySetInnerHTML={{ __html: styles }} />
      </>
    );
  });

  return <CacheProvider value={registry.cache}>{children}</CacheProvider>;
}
