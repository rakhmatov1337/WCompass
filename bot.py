import os
from datetime import datetime
import pytz
import django
import random
from collections import defaultdict
from aiogram.dispatcher.filters import Text
from django.core.files import File
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types.webhook_info import WebhookInfo
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup,
                           KeyboardButton, ReplyKeyboardMarkup,
                           ReplyKeyboardRemove)
from asgiref.sync import sync_to_async
from decimal import Decimal
from django.utils.timezone import localtime
from django.utils import timezone
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WCompass.settings')
django.setup()
from main.models import Company, VacancyType, RequirementTech, Vacancy, Locations

bot = Bot('7031018913:AAHfL4zWtIkMp2kjoJEaS6hLWQoP0scIC6A')
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

class CompanyAddForm(StatesGroup):
    name = State()
    logo = State()
    location = State()

class VacancyTypeAddForm(StatesGroup):
    name = State()

class RequirementTechAddForm(StatesGroup):
    name = State()

class VacancyAddForm(StatesGroup):
    name = State()
    company = State()
    start_date = State()
    detail = State()
    vacancy_type = State()
    requirement_tech = State()

@dp.message_handler(commands=['start'])
async def Start_Command(message: types.Message):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton("start", web_app=WebhookInfo(url='https://celadon-paprenjak-cb9a3b.netlify.app/')))
    await message.answer("Hello", reply_markup=markup)


@dp.message_handler(commands=['add_company'], state='*')
async def start_add_company(message: types.Message):
    await CompanyAddForm.name.set()
    await message.reply("Please enter the company's name:")

@dp.message_handler(state=CompanyAddForm.name)
async def company_name_entered(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await CompanyAddForm.next()
    await message.reply("Please upload the company's logo:")


@dp.message_handler(content_types=['photo'], state=CompanyAddForm.logo)
async def company_logo_uploaded(message: types.Message, state: FSMContext):
    # Get the best quality photo
    photo = message.photo[-1]
    file_info = await bot.get_file(photo.file_id)
    file_path = file_info.file_path

    # Download the photo
    file = await bot.download_file(file_path)

    # Save the file temporarily
    temp_file_path = f"temp_{random.randint(1, 10000)}.jpg"
    with open(temp_file_path, 'wb') as image_file:
        image_file.write(file.read())

    # Ensure the file is closed before proceeding
    try:
        # Open the file again to create a Django File object
        with open(temp_file_path, 'rb') as image_file:
            django_file = File(image_file, name=os.path.basename(temp_file_path))

            # Use Django model to save the file properly
            logo_path = await sync_to_async(save_logo)(django_file, message.from_user.id)

            # Update state with the logo path
            await state.update_data(logo=logo_path)

        # Clean up the local file
        os.remove(temp_file_path)
    except Exception as e:
        # Handle exceptions and cleanup
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        await message.reply(f"Failed to upload logo. Error: {str(e)}")
        return

    # Set the next state
    await CompanyAddForm.location.set()

    # Prompt for the next input
    await message.reply("Please select the company's location:", reply_markup=await generate_location_keyboard())

def save_logo(django_file, user_id):
    company = Company.objects.create(name="Temporary Name", logo=django_file)
    logourl = company.logo.url
    company.delete()
    return logourl



@dp.callback_query_handler(lambda c: c.data.startswith('loc_'), state=CompanyAddForm.location)
async def location_button_pressed(callback_query: types.CallbackQuery, state: FSMContext):
    data = callback_query.data
    if data == "loc_done":
        await create_company(state)
        await state.finish()
        await callback_query.message.answer("Company created successfully!")
    else:
        location_id = int(data.split('_')[1])
        location = await sync_to_async(Locations.objects.get)(id=location_id)
        selected_locations = await state.get_data()
        selected_locations = selected_locations.get("selected_locations", [])
        if location.name not in selected_locations:
            selected_locations.append(location.name)
        await state.update_data(selected_locations=selected_locations)
        await callback_query.answer("Location added.")

@dp.message_handler(commands=['add_vacancy_type'], state='*')
async def start_add_vacancy_type(message: types.Message):
    await VacancyTypeAddForm.name.set()
    await message.reply("Please enter the vacancy type name:")

@dp.message_handler(state=VacancyTypeAddForm.name)
async def vacancy_type_name_entered(message: types.Message, state: FSMContext):
    await create_vacancy_type(state)
    await state.finish()
    await message.reply("Vacancy type added successfully!")

async def create_vacancy_type(state: FSMContext):
    data = await state.get_data()
    new_vacancy_type = VacancyType(name=data['name'])
    new_vacancy_type.save()

@dp.message_handler(commands=['add_requirement_tech'], state='*')
async def start_add_requirement_tech(message: types.Message):
    await RequirementTechAddForm.name.set()
    await message.reply("Please enter the tech requirement name:")

@dp.message_handler(state=RequirementTechAddForm.name)
async def requirement_tech_name_entered(message: types.Message, state: FSMContext):
    await create_requirement_tech(state)
    await state.finish()
    await message.reply("Tech requirement added successfully!")

@dp.message_handler(commands=['add_vacancy'], state='*')
async def start_add_vacancy(message: types.Message):
    await VacancyAddForm.name.set()
    await message.reply("Please enter the vacancy name:")

@dp.message_handler(state=VacancyAddForm.name)
async def vacancy_name_entered(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await VacancyAddForm.next()
    await message.reply("Please select the company:", reply_markup=await generate_company_keyboard())

@dp.callback_query_handler(lambda c: c.data.startswith('company_'), state=VacancyAddForm.company)
async def company_selected(callback_query: types.CallbackQuery, state: FSMContext):
    company_id = int(callback_query.data.split('_')[1])
    await state.update_data(company=company_id)
    await callback_query.message.edit_text("Company selected. Please enter the start date (YYYY-MM-DD):")
    await VacancyAddForm.next()

@dp.message_handler(state=VacancyAddForm.start_date)
async def start_date_entered(message: types.Message, state: FSMContext):
    # Attempt to parse the date string from the message
    try:
        # Ensure the date is in the correct format
        parsed_date = datetime.strptime(message.text, "%Y.%m.%d").date()
        formatted_date = parsed_date.strftime("%Y-%m-%d")
        await state.update_data(start_date=formatted_date)
        await VacancyAddForm.next()
        await message.reply("Please enter the vacancy detail:")
    except ValueError:
        # Send an error message if the date format is incorrect
        await message.reply("Invalid date format. Please use YYYY.MM.DD format.")

@dp.message_handler(state=VacancyAddForm.detail)
async def detail_entered(message: types.Message, state: FSMContext):
    await state.update_data(detail=message.text)
    await VacancyAddForm.next()
    await message.reply("Please select the vacancy type(s):", reply_markup=await generate_vacancy_type_keyboard())

@dp.callback_query_handler(lambda c: c.data.startswith('vtype_') or c.data == 'vtype_done', state=VacancyAddForm.vacancy_type)
async def vacancy_type_selected(callback_query: types.CallbackQuery, state: FSMContext):
    data = callback_query.data
    if data == "vtype_done":
        await callback_query.message.edit_text("Now select requirement tech(s):", reply_markup=await generate_requirement_tech_keyboard())
        await VacancyAddForm.next()
    else:
        vt_id = int(data.split('_')[1])
        current_selection = await state.get_data()
        current_selection = current_selection.get("vacancy_types", [])
        current_selection.append(vt_id)
        await state.update_data(vacancy_types=current_selection)
        await callback_query.answer("Vacancy Type added.")

@dp.callback_query_handler(lambda c: c.data.startswith('rtech_') or c.data == 'rtech_done', state=VacancyAddForm.requirement_tech)
async def requirement_tech_selected(callback_query: types.CallbackQuery, state: FSMContext):
    data = callback_query.data
    if data == "rtech_done":
        try:
            user_data = await state.get_data()
            await callback_query.message.edit_text("All data collected. Creating vacancy...")
            await create_vacancy(user_data)
            await state.finish()
            await callback_query.message.edit_text("Vacancy added")
        except:
            await callback_query.message.edit_text("Error try aging")
    else:
        rt_id = int(data.split('_')[1])
        current_selection = await state.get_data()
        current_selection = current_selection.get("requirement_techs", [])
        current_selection.append(rt_id)
        await state.update_data(requirement_techs=current_selection)
        await callback_query.answer("Requirement Tech added.")

async def create_vacancy(data):
    company = await sync_to_async(Company.objects.get)(id=data['company'])
    vacancy = Vacancy(name=data['name'], company=company, start_date=data['start_date'], detail=data['detail'])
    await sync_to_async(vacancy.save)()
    for vt_id in data['vacancy_types']:
        vt = await sync_to_async(VacancyType.objects.get)(id=vt_id)
        await sync_to_async(vacancy.vacancy_type.add)(vt)
    for rt_id in data['requirement_techs']:
        rt = await sync_to_async(RequirementTech.objects.get)(id=rt_id)
        await sync_to_async(vacancy.requirement_tech.add)(rt)

async def create_requirement_tech(state: FSMContext):
    data = await state.get_data()
    new_requirement_tech = RequirementTech(name=data['name'])
    new_requirement_tech.save()

async def generate_company_keyboard():
    companies = await sync_to_async(list)(Company.objects.all())
    keyboard = InlineKeyboardMarkup()
    for company in companies:
        keyboard.add(InlineKeyboardButton(company.name, callback_data=f"company_{company.id}"))
    return keyboard

async def generate_location_keyboard():
    locations = await sync_to_async(list)(Locations.objects.all())
    keyboard = InlineKeyboardMarkup(row_width=1)
    for location in locations:
        button = InlineKeyboardButton(location.name, callback_data=f"loc_{location.id}")
        keyboard.add(button)
    keyboard.add(InlineKeyboardButton("Done", callback_data="loc_done"))
    return keyboard


async def create_company(state: FSMContext):
    data = await state.get_data()
    new_company = await sync_to_async(Company.objects.create)(name=data['name'], logo=data['logo'])
    for location_name in data['selected_locations']:
        location = await sync_to_async(Locations.objects.get)(name=location_name)
        await sync_to_async(new_company.location.add)(location)
    await sync_to_async(new_company.save)()

async def generate_vacancy_type_keyboard():
    vacancy_types = await sync_to_async(list)(VacancyType.objects.all())
    keyboard = InlineKeyboardMarkup()
    for vt in vacancy_types:
        keyboard.add(InlineKeyboardButton(vt.name, callback_data=f"vtype_{vt.id}"))
    keyboard.add(InlineKeyboardButton("Done", callback_data="vtype_done"))
    return keyboard


async def generate_requirement_tech_keyboard():
    requirement_techs = await sync_to_async(list)(RequirementTech.objects.all())
    keyboard = InlineKeyboardMarkup()
    for rt in requirement_techs:
        keyboard.add(InlineKeyboardButton(rt.name, callback_data=f"rtech_{rt.id}"))
    keyboard.add(InlineKeyboardButton("Finish", callback_data="rtech_done"))
    return keyboard



# async def create_vacancy(data):
#     company = Company.objects.get(id=data['company'])
#     vacancy = Vacancy(
#         name=data['name'],
#         company=company,
#         start_date=data['start_date'],
#         detail=data['detail']
#     )
#     vacancy.save()
#     for vt_id in data['vacancy_types']:
#         vacancy.vacancy_type.add(VacancyType.objects.get(id=vt_id))
#     for rt_id in data['requirement_techs']:
#         vacancy.requirement_tech.add(RequirementTech.objects.get(id=rt_id))
#     vacancy.save()




if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
