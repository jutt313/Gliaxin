export declare class HttpClient {
    private readonly headers;
    private readonly baseUrl;
    private readonly timeout;
    constructor(apiKey: string, baseUrl: string, timeout: number);
    get<T>(path: string, params?: Record<string, unknown>): Promise<T>;
    post<T>(path: string, body?: Record<string, unknown>): Promise<T>;
    delete<T>(path: string, body?: Record<string, unknown>): Promise<T>;
}
//# sourceMappingURL=http.d.ts.map