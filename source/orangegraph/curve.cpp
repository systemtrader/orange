#include "curve.h"

#include <QtCore/QDebug>
#include <QtGui/QBrush>
#include <QtGui/QPen>

Curve::Curve(QList< double > xData, QList< double > yData, QGraphicsItem* parent, QGraphicsScene* scene): PlotItem(xData, yData, parent, scene)
{
    m_continuous = false;
    m_lineItem = 0;
    setData(xData, yData);
}

Curve::~Curve()
{

}

void Curve::updateNumberOfItems()
{
  if (m_continuous)
  {
    return;
  }
  int n = m_data.size();
  if (m_pointItems.size() > n)
  {
    qDeleteAll(m_pointItems.begin() + n, m_pointItems.end());
  }
  int m = n - m_pointItems.size();
  for (int i = 0; i < m; ++i)
  {
    QGraphicsPathItem * p = new QGraphicsPathItem(this);
    p->setPen(Qt::NoPen);
    m_pointItems.append(p);
  }
}

void Curve::updateProperties()
{
  
  if (m_continuous)
  {
    // Partial updates only make sense for discrete curves, because they have more properties
    updateAll();
    return;
  }
  
  int n = m_data.size();  

  if (m_needsUpdate & UpdateNumberOfItems)
  {
    updateNumberOfItems();
  }
  
  if (m_needsUpdate & (UpdateSize | UpdateSymbol))
  {
    m_path = pathForSymbol(m_symbol, m_pointSize);
    for (int i = 0; i < n; ++i)
    {
      m_pointItems[i]->setPath(m_path);
    }
  }
  
  // Move, resize, reshape and/or recolor the items
  if (m_needsUpdate & UpdatePosition)
  {
    QPointF p;
    QRectF dataRect = m_graphTransform.inverted().mapRect(m_graphArea);
    for (int i = 0; i < n; ++i)
    {
      p = QPointF(m_data[i].x, m_data[i].y);
      m_pointItems[i]->setPos(m_graphTransform.map(p));
    }
  }
  if (m_needsUpdate & UpdateColor)
  {
    QBrush brush(m_color);
    for (int i = 0; i < n; ++i)
    {
      m_pointItems[i]->setBrush(brush);
    }
  }
  m_needsUpdate = 0;
}

void Curve::updateAll()
{
  if (m_needsUpdate & UpdateContinuous)
  {
    changeContinuous();
  }
  
  if (m_continuous)
  {
    QPen pen;
    pen.setColor(m_color);
    pen.setWidth(m_pointSize);
    m_lineItem->setPen(pen);
    m_line = QPainterPath();
    m_line.moveTo(QPointF(m_data[0].x, m_data[0].y) * m_graphTransform);
    int n = m_data.size();
    QPointF p;
    for (int i = 1; i < n; ++i)
    {
      p = QPointF(m_data[i].x, m_data[i].y);
      m_line.lineTo(m_graphTransform.map(p));
    }
    m_lineItem->setPath(m_line);
  } 
  else 
  {
    if (m_needsUpdate & UpdateNumberOfItems)
    {
      updateNumberOfItems();
    }
    
    int n = m_data.size();
    QBrush brush(m_color);
    m_path = pathForSymbol(m_symbol, m_pointSize);
    QPointF p;
    for (int i = 0; i < n; ++i)
    {
      QGraphicsPathItem* item = m_pointItems[i];
      DataPoint& point = m_data[i];
      item->setPath(m_path);
      p = QPointF(point.x, point.x);
      item->setPos(p * m_graphTransform);
      item->setBrush(brush);
    }
  }
  m_needsUpdate = 0;
}


QGraphicsItem* Curve::pointItem(qreal x, qreal y, int size, QGraphicsItem* parent)
{
  if (size == 0)
  {
    size = pointSize();
  }
  if (parent == 0)
  {
    parent = this;
  }
  QGraphicsPathItem* item = new QGraphicsPathItem(pathForSymbol(symbol(),size), parent);
  item->setPos(x,y);
  item->setPen(Qt::NoPen);
  item->setBrush(m_color);
  return item;
}

QPainterPath Curve::pathForSymbol(int symbol, int size)
{
  QPainterPath path;
  qreal d = 0.5 * size;
  switch (symbol)
  {
    case Ellipse:
      path.addEllipse(-d,-d,d,d);
      break;
      
    case Rect:
      path.addRect(-d,-d,d,d);
      break;
      
    default:
      qWarning() << "Unsupported symbol" << symbol;
  }
  return path;
}

Data Curve::data() const
{
  return m_data;
}

void Curve::setData(const QList< qreal > xData, const QList< qreal > yData)
{
  Q_ASSERT(xData.size() == yData.size());
  int n = qMin(xData.size(), yData.size());
  if (n != m_data.size())
  {
    m_needsUpdate |= UpdateNumberOfItems;
  }
  m_data.clear();
  for (int i = 0; i < n; ++i)
  {
    DataPoint p;
    p.x = xData[i];
    p.y = yData[i];
    m_data.append(p);
  }
  m_needsUpdate |= UpdatePosition;
  updateBounds();
  checkForUpdate();
}

QTransform Curve::graphTransform() const
{
  return m_graphTransform;
}

void Curve::setGraphTransform(const QTransform& transform)
{
  if (transform == m_graphTransform)
  {
    return;
  }
  m_needsUpdate |= UpdatePosition;
  m_graphTransform = transform;
  checkForUpdate();
}

bool Curve::isContinuous() const
{
  return m_continuous;
}

void Curve::setContinuous(bool continuous)
{
  if (continuous == m_continuous)
  {
    return;
  }
  m_continuous = continuous;
  m_needsUpdate |= UpdateContinuous;
  checkForUpdate();
}

QColor Curve::color() const
{
  return m_color;
}

void Curve::setColor(const QColor& color)
{
  if (color == m_color)
  {
    return;
  }
  m_color = color;
  m_needsUpdate |= UpdateColor;
  checkForUpdate();
}

int Curve::pointSize() const
{
  return m_pointSize;
}

void Curve::setPointSize(int size)
{
  if (size == m_pointSize)
  {
    return;
  }
  
  m_pointSize = size;
  m_needsUpdate |= UpdateSize;
  checkForUpdate();
}

int Curve::symbol() const
{
  return m_symbol;
}

void Curve::setSymbol(int symbol)
{
  if (symbol == m_symbol)
  {
    return;
  }
  m_symbol = symbol;
  m_needsUpdate |= UpdateSymbol;
  checkForUpdate();
}

bool Curve::autoUpdate() const
{
  return m_autoUpdate;
}

void Curve::setAutoUpdate(bool autoUpdate)
{
  m_autoUpdate = autoUpdate;
  checkForUpdate();
}

QRectF Curve::graphArea() const
{
  return m_graphArea;
}

void Curve::setGraphArea(const QRectF& area)
{
  m_graphArea = area;
  m_needsUpdate |= UpdatePosition;
  checkForUpdate();
}

void Curve::checkForUpdate()
{
  if ( m_autoUpdate && m_needsUpdate )
  {
    updateProperties();
  }
}

void Curve::changeContinuous()
{
  if (m_continuous)
  {
    qDeleteAll(m_pointItems);
    m_pointItems.clear();
    
    if (!m_lineItem)
    {
      m_lineItem = new QGraphicsPathItem(this);
    }
  } else {
    m_line = QPainterPath();
    delete m_lineItem;
    m_lineItem = 0;
  }
}

void Curve::updateBounds()
{
    int n = m_data.size();
    if (!n)
    {
        m_xBounds.min = 0;
        m_xBounds.max = 0;
        m_yBounds.min = 0;
        m_yBounds.max = 0;
        return;
    }

    m_xBounds.min = m_xBounds.max = m_data[0].x;
    m_yBounds.min = m_yBounds.max = m_data[0].y;
    for (int i = 0; i < n; ++i)
    {
        m_xBounds.min = qMin(m_xBounds.min, m_data[i].x);
        m_xBounds.max = qMax(m_xBounds.max, m_data[i].x);
        m_yBounds.min = qMin(m_yBounds.min, m_data[i].y);
        m_yBounds.max = qMax(m_yBounds.max, m_data[i].y);
    }
}

qreal Curve::max_x_value() const
{
    return m_xBounds.max;
}

qreal Curve::min_x_value() const
{
    return m_yBounds.min;
}


qreal Curve::max_y_value() const
{
    return m_yBounds.max;
}

qreal Curve::min_y_value() const
{
    return m_yBounds.min;
}