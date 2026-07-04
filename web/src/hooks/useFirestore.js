import { useEffect, useState } from "react";
import { collection, doc, onSnapshot, query } from "firebase/firestore";
import { db } from "../firebase";
import { PREVIEW } from "../dev/preview";
import { previewCollection, previewDoc } from "../dev/fixtures";

/**
 * Live collection via onSnapshot. `constraints` = where()/orderBy()/limit() list.
 * `deps` = the raw values those constraints were built from (e.g. `[districtId]`),
 * used to detect when the query actually needs to change — Firestore's
 * QueryConstraint objects don't stringify meaningfully (String(where(...)) is
 * always "[object Object]"), so re-subscribing can't rely on the constraints
 * array itself.
 */
export function useCollection(path, constraints = [], deps = []) {
  const [rows, setRows] = useState(PREVIEW ? previewCollection(path) : []);
  useEffect(() => {
    if (PREVIEW) return; // fixtures are static in preview mode
    const q = query(collection(db, path), ...constraints);
    return onSnapshot(q, (snap) =>
      setRows(snap.docs.map((d) => ({ id: d.id, ...d.data() })))
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, ...deps]);
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
