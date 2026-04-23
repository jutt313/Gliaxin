import { AuthError, NotFoundError, ValidationError, RateLimitError, ServerError, GliaxinError, } from './errors.js';
async function throwForStatus(res) {
    let detail = 'Unknown error';
    try {
        const body = await res.json();
        detail = body?.detail ?? detail;
    }
    catch { /* ignore */ }
    switch (res.status) {
        case 400: throw new ValidationError(detail);
        case 401: throw new AuthError(detail);
        case 404: throw new NotFoundError(detail);
        case 429: throw new RateLimitError(detail);
    }
    if (res.status >= 500)
        throw new ServerError(detail, res.status);
    throw new GliaxinError(detail, res.status);
}
export class HttpClient {
    headers;
    baseUrl;
    timeout;
    constructor(apiKey, baseUrl, timeout) {
        this.headers = {
            'X-Api-Key': apiKey,
            'Content-Type': 'application/json',
        };
        this.baseUrl = baseUrl.replace(/\/$/, '');
        this.timeout = timeout;
    }
    async get(path, params) {
        const url = new URL(`${this.baseUrl}${path}`);
        if (params) {
            for (const [k, v] of Object.entries(params)) {
                if (v !== undefined && v !== null)
                    url.searchParams.set(k, String(v));
            }
        }
        const res = await fetch(url.toString(), {
            method: 'GET',
            headers: this.headers,
            signal: AbortSignal.timeout(this.timeout),
        });
        if (!res.ok)
            await throwForStatus(res);
        return res.json();
    }
    async post(path, body) {
        const res = await fetch(`${this.baseUrl}${path}`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify(body ?? {}),
            signal: AbortSignal.timeout(this.timeout),
        });
        if (!res.ok)
            await throwForStatus(res);
        return res.json();
    }
    async delete(path, body) {
        const res = await fetch(`${this.baseUrl}${path}`, {
            method: 'DELETE',
            headers: this.headers,
            body: JSON.stringify(body ?? {}),
            signal: AbortSignal.timeout(this.timeout),
        });
        if (!res.ok)
            await throwForStatus(res);
        return res.json();
    }
}
//# sourceMappingURL=http.js.map