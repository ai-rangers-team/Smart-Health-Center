import { useEffect, useState } from "react";
import { collection, doc, onSnapshot, query } from "firebase/firestore";
import { db } from "../firebase";
import { PREVIEW } from "../dev/preview";
import { previewCollection, previewDoc } from "../dev/fixtures";

/** Live collection via onSnapshot. `constraints` = where()/orderBy()/limit() list. */
export function useCollection(path, constraints = []) {
  const [rows, setRows] = useState(PREVIEW ? previewCollection(path) : []);
  useEffect(() => {
    if (PREVIEW) return; // fixtures are static in preview mode
    const q = query(collection(db, path), ...constraints);
    return onSnapshot(q, (snap) =>
      setRows(snap.docs.map((d) => ({ id: d.id, ...d.data() })))
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, JSON.stringify(constraints.map(String))]);
  return rows;
}

/** Live single document via onSnapshot. */
export function useDoc(path) {
  const [data, setData] = useState(PREVIEW ? previewDoc(path) : null);
  useEffect(() => {
    if (PREVIEW) return;
    return onSnapshot(doc(db, path), (d) =>
      setData(d.exists() ? { id: d.id, ...d.data() } : null)
    );
  }, [path]);
  return data;
}
