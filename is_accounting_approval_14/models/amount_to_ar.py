#!/usr/bin/env python
# -*- coding: utf-8 -*-
##############################################################################
#    Description: Convert to numbers to arabic words                         #
#    Author: IntelliSoft Software                                            #
#    Date: Aug 2015 -  Till Now                                              #
##############################################################################

to_19_ar = (u'صفر', u'واحد', u'اثنان', u'ثلاثة', u'أربعة', u'خمسة', u'ستة',
            u'سبعة', u'ثمانية', u'تسعة', u'عشرة', u'أحد عشر', u'اثنا عشر', u'ثلاثة عشر',
            u'أربعة عشرة', u'خمسة عشر', u'ست عشرة', u'سبعة عشر', u'ثمانية عشر', u'تسعة عشر')

tens_ar = (u'', u'', u'عشرون', u'ثلاثون', u'أربعون', u'خمسون', u'ستون', u'سبعون', u'ثمانون', u'تسعون')

hund_ar = (u'', u'مئة', u'مئتان', u'ثلاثمئة', u'اربعمئة', u'خمسمئة', u'ستمئة', u'سبعمئة', u'ثمانمئة', u'تسعمئة')


def convert_less_100(number):
    if number <= 19:
        return to_19_ar[int(number)]
    elif number < 100:
        ten = number / 10
        rest = number % 10
        if rest != 0:
            return to_19_ar[int(rest)] + u' و ' + tens_ar[int(ten)]
        else:
            return tens_ar[int(ten)]


def convert_less_1000(number):
    hund = number / 100
    rest = number % 100
    if hund == 0:
        hund_text = u''
    elif hund == 1:
        hund_text = u'مئة'
    elif hund < 10:
        hund_text = hund_ar[int(hund)]
    else:
        hund_text = convert_less_1000(hund) + u' مئة '
    if rest != 0:
        if hund_text != u'':
            hund_text = hund_text + u' و ' + convert_to_ar(rest)
        else:
            hund_text = convert_to_ar(rest)
    return hund_text


def convert_less_10000(number):
    thous = number / 1000
    rest = number % 1000
    if thous == 0:
        thous_text = u''
    elif thous == 1:
        thous_text = u'الف'
    elif thous >= 2 and thous < 3:
        thous_text = u'الفين'
    elif thous <= 10:
        thous_text = convert_less_100(thous) + u' آلاف'
    else:
        thous_text = convert_less_1000(thous) + u' الف'
    if rest != 0:
        if thous_text != u'':
            thous_text = thous_text + u' و ' + convert_to_ar(rest)
        else:
            thous_text = convert_to_ar(rest)
    return thous_text


def convert_less_billion(number):
    million = number / 1000000
    rest = number % 1000000
    if million >= 1 and million <2:
        million_text = u'مليون'
    elif million == 2:
        million_text = u'مليونين'
    elif million <= 10:
        million_text = convert_less_100(million) + u' ' + u'ملايين'
    else:
        million_text = convert_less_1000(million) + u' ' + u'مليون'
    if rest != 0:
        million_text = million_text + u' و ' + convert_to_ar(rest)
    return million_text


def convert_over_billion(number):
    million = number / 1000000000
    rest = number % 1000000000
    if million == 1:
        million_text = u'مليار'
    elif million == 2:
        million_text = u'مليارين'
    elif million <= 10:
        million_text = convert_less_100(million) + u' ' + u'ملايير'
    else:
        million_text = convert_less_1000(million) + u' ' + u'مليار'
    if rest != 0:
        million_text = million_text + u' و ' + convert_to_ar(rest)
    return million_text


def convert_to_ar(number):
    if number < 100:
        return convert_less_100(number)
    elif number < 1000 and number >= 100:
        return convert_less_1000(number)
    elif number < 1000000 and number >= 1000:
        return convert_less_10000(number)
    elif number < 1000000000 and number >= 1000000:
        return convert_less_billion(number)
    else:
        return convert_over_billion(number)


def amount_to_text_ar(number, un, cn):
    number = '%.2f' % number
    units_name = u' ' + str(un) + u' '
    list = str(number).split('.')
    start_word = convert_to_ar(abs(int(list[0])))
    end_word = convert_to_ar(int(list[1]))
    cents_number = int(list[1])
    cents_name = (cents_number > 1) and (u' ' + str(cn) + u' ') or (u' ' + str(cn) + u' ')
    final_result = start_word + u' ' + units_name + u' و ' + end_word + u' ' + cents_name
    return final_result