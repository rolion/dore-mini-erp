export class FAQS {
  public id: number;
  public title: string;
  public content: string;

  constructor(faqId: number, title: string, content: string) {
    this.id = faqId;
    this.title = title;
    this.content = content;
  }
}
