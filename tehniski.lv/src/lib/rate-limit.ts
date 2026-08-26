type Bucket = { tokens: number; refilledAt: number };
export class TokenBucket {
  private buckets = new Map<string, Bucket>();
  constructor(private capacity: number, private windowMs: number) {}
  tryConsume(key: string): boolean {
    const now = Date.now();
    const b = this.buckets.get(key);
    if (!b || now - b.refilledAt >= this.windowMs) {
      this.buckets.set(key, { tokens: this.capacity - 1, refilledAt: now });
      return true;
    }
    if (b.tokens <= 0) return false;
    b.tokens -= 1;
    return true;
  }
}
