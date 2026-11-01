/** Автообновление клиентов — правь после pack_updates.py + заливки zip на CDN. */
export const UPDATES_MANIFEST = {
  schema: 1,
  channel: "stable",
  released: "2026-11-01T00:00:00Z",
  products: {
    cloner: {
      version: "2026.11.01.1",
      zip: "",
      sha256: "",
      exe: { url: "", sha256: "" },
    },
    bot: { version: "2026.11.01.1", zip: "", sha256: "" },
    ascii: { version: "2026.11.01.1", zip: "", sha256: "" },
    bundle: { version: "2026.11.01.1", zip: "", sha256: "" },
  },
};
