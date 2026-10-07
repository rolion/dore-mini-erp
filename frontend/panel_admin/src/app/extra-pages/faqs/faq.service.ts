import { FAQS } from './faqs.model';
import { Injectable } from '@angular/core';

@Injectable()
export class FaqService {
  constructor() {}

  public faqs: FAQS[] = [
    new FAQS(
      1,
      'HOW CAN I CHANGE MY SHIPPING ADDRESS?',
      'By default, the last used shipping address will be saved into to your Sample Store account. When you are checking out your order, the default shipping address will be displayed and you have the option to amend it if you need to.'
    ),
    new FAQS(
      2,
      'HOW DO I ACTIVATE MY ACCOUNT?',
      'The instructions to activate your account will be sent to your email once you have submitted the registration form. If you did not receive this email, your email service provider’s mailing software may be blocking it.'
    ),
    new FAQS(
      3,
      'WHAT DO YOU MEAN BY POINTS? HOW DO I EARN IT?',
      'Because you are important to us, we want to know what you think about the products. As an added value, every time you rate the products you earn points which go straight to your account. 1 point are added to your account for every review that you give.'
    ),
    new FAQS(
      4,
      'WHY IS THERE A CHECKOUT LIMIT? / WHAT ARE ALL THE CHECKOUT LIMITS?',
      'Sample Store is a popular spot and gets lots of shoppers at a time. These limits are in place to make sure everyone has a good time trying and purchasing their products. So...'
    ),
    new FAQS(
      5,
      'HOW CAN I TRACK MY ORDERS & PAYMENT?',
      'After logging into your account, the status of your checkout history can be found under Order History. For orders via registered postage, a tracking number (article tracking number) will be given to you after the receipt given from Singapore Post Limited (SingPost).'
    ),
    new FAQS(
      6,
      'HOW DO I CANCEL MY ORDERS BEFORE I MAKE A PAYMENT?',
      'After logging into your account, go to your Shopping Cart. Here, you will be able to make payment or cancel your order. Note: We cannot give refunds once payment is verified.'
    ),
    new FAQS(
      7,
      'HOW LONG WILL IT TAKE FOR MY ORDER TO ARRIVE AFTER I MAKE PAYMENT?',
      'Members who ship their orders within Singapore should expect to receive their orders within five (5) to ten (10) working days upon payment verification depending on the volume of orders received.'
    ),
    new FAQS(
      8,
      'HOW DO YOU SHIP MY ORDERS?',
      'All your orders are sent via Singapore Post Limited (SingPost).'
    ),
    new FAQS(
      9,
      'HOW CAN I USE MY REMAINING ACCOUNT CREDITS?',
      'We are in the process of removing the option to pay for your orders by ‘Account Credits’. If you have remaining credits in your account, it will be used to pay for your next checkout. '
    ),
    new FAQS(
      10,
      'WHY MUST I MAKE PAYMENT IMMEDIATELY AT CHECKOUT?',
      'Sample ordering is on ‘first-come-first-served’ basis. To ensure that you get your desired samples, it is recommended that you make your payment within 60 minutes of checking out.'
    ),
  ];
}
