# Sc## Features

- **Multi-day Display**: Show 1-5 days of menu items starting from today
- **Weekend Skipping**: Automatically skips Saturday and Sunday when fetching school days
- **Smart Filtering**: Filters out standard lunch items (Garden Bar, Milk, etc.)
- **Custom URL Support**: Parse menu data from any web URL  
- **Flexible Layout**: Adapts to single or multi-day display formats
- **Font Size Control**: Choose from 7 font sizes (Extra Small to Extra Large)
- **Customizable Title**: Set your own display title
- **Optional Date Display**: Show/hide date information
- **Automatic Fallback**: Uses mock data if URL parsing fails
- **Clean Layout**: Organized with bullet points and day headers
- **Automatic Refresh Timestamp**: Shows when the data was last updated
- **Multi-display Support**: Works with both black & white and color displayslugin for InkyPi

A plugin that displays school lunch menu information on your InkyPi e-ink display with support for custom URL parsing and multi-day menu display.

## Features

- **Multi-day Display**: Show 1-5 days of menu items starting from today
- **Custom URL Support**: Parse menu data from any web URL  
- **Flexible Layout**: Adapts to single or multi-day display formats
- **Customizable Title**: Set your own display title
- **Optional Date Display**: Show/hide date information
- **Automatic Fallback**: Uses mock data if URL parsing fails
- **Clean Layout**: Organized with bullet points and day headers
- **Automatic Refresh Timestamp**: Shows when data was last updated
- **Multi-display Support**: Works with both black & white and color displays

## Files Structure

```
schoolmenu/
├── plugin-info.json      # Plugin metadata
├── schoolmenu.py         # Main plugin class
├── lunch_menu_service.py # Service for getting menu data
├── settings.html         # Plugin settings form
├── icon.png             # Plugin icon
└── README.md            # This file
```

## Configuration Options

The plugin provides the following settings:

- **Menu URL**: Enter a URL where menu data can be found (optional - uses mock data if empty)
- **Number of Days**: Display 1-5 days of menu data (1 Day, 2 Days, 3 Days, 4 Days, 5 Days (Work Week))
- **Custom Title**: Set a custom title for the display (default: "School Lunch Menu")
- **Font Size**: Choose font size from Extra Small to Extra Large (default: Normal)
- **Show Date**: Toggle whether to display the date (for single day) or day headers (for multi-day)
- **Show Refresh Time**: Toggle whether to display when the data was last refreshed

## Smart Features

### Weekend Skipping
The plugin automatically skips weekends (Saturday and Sunday) when generating multiple days of menus, ensuring you only see school days.

### Item Filtering
Standard lunch items are automatically filtered out to focus on the main meal options:
- Garden Bar and variations
- Milk options (Organic, Low-fat, Non-fat, etc.)
- Generic "Fresh Fruits and Veggies" items

### Font Scaling
Font sizes are applied consistently across all text elements:
- Title: 24pt base × scale factor
- Date headers: 16pt base × scale factor  
- Menu items: 14pt base × scale factor
- Small text/timestamps: 12pt base × scale factor

### Current Implementation
- The plugin accepts any URL in the Menu URL field
- Currently falls back to mock data with a warning (URL parsing not yet implemented)
- Ready for extension to parse actual menu data from web sources

### Future Extensions
To integrate with a real school menu system:

1. **Extend `_fetch_menu_from_url()` method** in `lunch_menu_service.py`
2. **Add parsing logic** for your specific menu format (HTML, JSON, CSV, etc.)
3. **Handle different URL formats** (direct data URLs, web pages, APIs)
4. **Add error handling** for network issues and parsing failures

### Example Integration Ideas
- Parse HTML tables from school websites
- Fetch JSON data from school APIs  
- Import CSV files from nutrition services
- Scrape PDF menu documents
- **Custom Title**: Set a custom title for the display (default: "School Lunch Menu")
- **Show Date**: Toggle whether to display the date
- **Show Refresh Time**: Toggle whether to display when the data was last refreshed

## Mock Data

Currently, the plugin uses mock data for demonstration. The `LunchMenuService` includes sample menus for several dates in September/October 2025. When no URL is provided or URL fetching fails, the plugin automatically generates default menu items for the requested number of days.

## Layout Design

### Single Day Display
- Centered title with accent color
- Full date display (if enabled)
- Horizontal separator line  
- Bullet-pointed menu items
- Bottom refresh timestamp

### Multi-Day Display  
- Centered title with accent color
- Day headers (Today, Tomorrow, or day names)
- Compact date format (MM/DD) in headers if enabled
- Indented bullet-pointed menu items for each day
- Automatic space management with truncation
- Bottom refresh timestamp

The layout automatically adjusts to available space and truncates long content with indicators showing remaining items or days.

## Installation

The plugin is ready to use once the files are placed in the `src/plugins/schoolmenu/` directory of your InkyPi installation. The plugin will automatically appear in the InkyPi web interface.